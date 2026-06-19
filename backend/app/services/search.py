import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.schemas.search import SearchFilters, SearchResult, SearchResponse, ScoreBreakdown
import structlog

logger = structlog.get_logger()


class SearchService:
    WEIGHTS = {"keyword": 0.4, "semantic": 0.4, "graph": 0.2}

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query: str,
        filters: SearchFilters | None = None,
        limit: int = 20,
    ) -> SearchResponse:
        if filters is None:
            filters = SearchFilters()

        start = time.monotonic()
        search_types: list[str] = []

        keyword_results: list[SearchResult] = []
        semantic_results: list[SearchResult] = []

        if filters.search_type in ("all", "keyword"):
            keyword_results = await self.keyword_search(query, filters, limit)
            search_types.append("keyword")

        if filters.search_type in ("all", "semantic"):
            # Only do semantic if we have embeddings available
            semantic_results = await self.semantic_search(query, filters, limit)
            if semantic_results:
                search_types.append("semantic")

        merged = self._merge_results(keyword_results, semantic_results, [])
        merged = merged[:limit]

        latency = int((time.monotonic() - start) * 1000)

        return SearchResponse(
            query=query,
            results=merged,
            total=len(merged),
            latency_ms=latency,
            search_types_used=search_types,
        )

    async def keyword_search(
        self, query: str, filters: SearchFilters, limit: int
    ) -> list[SearchResult]:
        params: dict = {"query": query, "lim": limit}
        extra = ""
        if filters.language:
            extra += " AND p.language = :lang"
            params["lang"] = filters.language
        if filters.framework:
            extra += " AND p.framework = :fw"
            params["fw"] = filters.framework
        if filters.project_slug:
            extra += " AND p.slug = :proj"
            params["proj"] = filters.project_slug

        sql = text(f"""
            SELECT
                dc.id::text AS chunk_id,
                dc.chunk_text,
                d.title AS document_title,
                d.type AS document_type,
                p.name AS project_name,
                p.slug AS project_slug,
                ts_rank_cd(dc.tsv, plainto_tsquery('english', :query)) AS rank,
                ts_headline(
                    'english',
                    substring(dc.chunk_text, 1, 500),
                    plainto_tsquery('english', :query),
                    'MaxWords=30, MinWords=10, StartSel=<mark>, StopSel=</mark>'
                ) AS highlight
            FROM search.document_chunks dc
            JOIN core.documents d ON d.id = dc.document_id
            JOIN core.projects p ON p.id = dc.project_id
            WHERE dc.tsv @@ plainto_tsquery('english', :query){extra}
            ORDER BY rank DESC
            LIMIT :lim
        """)

        try:
            result = await self.db.execute(sql, params)
            rows = result.fetchall()
        except Exception as e:
            logger.warning("keyword_search_error", error=str(e))
            return []

        if not rows:
            return []

        max_rank = max(r.rank for r in rows) or 1.0
        return [
            SearchResult(
                chunk_id=r.chunk_id,
                chunk_text=r.chunk_text,
                document_title=r.document_title,
                document_type=r.document_type,
                project_name=r.project_name,
                project_slug=r.project_slug,
                score=float(r.rank) / max_rank,
                score_breakdown=ScoreBreakdown(keyword=float(r.rank) / max_rank),
                highlight=r.highlight or "",
            )
            for r in rows
        ]

    async def semantic_search(
        self, query: str, filters: SearchFilters, limit: int
    ) -> list[SearchResult]:
        # Requires embeddings and pgvector — skip gracefully if not available
        try:
            from app.services.embedding import EmbeddingService
            emb_service = EmbeddingService(self.db)
            embedding = await emb_service.embed_text(query)
            if not embedding:
                return []

            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            threshold = filters.min_score
            sparams: dict = {"emb": embedding_str, "threshold": threshold, "lim": limit}
            sextra = ""
            if filters.language:
                sextra += " AND p.language = :lang"
                sparams["lang"] = filters.language
            if filters.framework:
                sextra += " AND p.framework = :fw"
                sparams["fw"] = filters.framework
            if filters.project_slug:
                sextra += " AND p.slug = :proj"
                sparams["proj"] = filters.project_slug

            sql = text(f"""
                SELECT
                    dc.id::text AS chunk_id,
                    dc.chunk_text,
                    d.title AS document_title,
                    d.type AS document_type,
                    p.name AS project_name,
                    p.slug AS project_slug,
                    1 - (dc.embedding <=> :emb::vector) AS similarity
                FROM search.document_chunks dc
                JOIN core.documents d ON d.id = dc.document_id
                JOIN core.projects p ON p.id = dc.project_id
                WHERE dc.embedding IS NOT NULL
                  AND 1 - (dc.embedding <=> :emb::vector) > :threshold{sextra}
                ORDER BY dc.embedding <=> :emb::vector
                LIMIT :lim
            """)

            result = await self.db.execute(sql, sparams)
            rows = result.fetchall()

            return [
                SearchResult(
                    chunk_id=r.chunk_id,
                    chunk_text=r.chunk_text,
                    document_title=r.document_title,
                    document_type=r.document_type,
                    project_name=r.project_name,
                    project_slug=r.project_slug,
                    score=float(r.similarity),
                    score_breakdown=ScoreBreakdown(semantic=float(r.similarity)),
                    highlight="",
                )
                for r in rows
            ]
        except Exception as e:
            logger.debug("semantic_search_unavailable", error=str(e))
            return []

    def _merge_results(
        self,
        keyword: list[SearchResult],
        semantic: list[SearchResult],
        graph: list[SearchResult],
    ) -> list[SearchResult]:
        scores: dict[str, dict] = {}

        for r in keyword:
            scores[r.chunk_id] = {"result": r, "keyword": r.score, "semantic": 0.0, "graph": 0.0}

        for r in semantic:
            if r.chunk_id in scores:
                scores[r.chunk_id]["semantic"] = r.score
            else:
                scores[r.chunk_id] = {"result": r, "keyword": 0.0, "semantic": r.score, "graph": 0.0}

        for r in graph:
            if r.chunk_id in scores:
                scores[r.chunk_id]["graph"] = r.score
            else:
                scores[r.chunk_id] = {"result": r, "keyword": 0.0, "semantic": 0.0, "graph": r.score}

        final: list[SearchResult] = []
        for data in scores.values():
            combined = (
                self.WEIGHTS["keyword"] * data["keyword"]
                + self.WEIGHTS["semantic"] * data["semantic"]
                + self.WEIGHTS["graph"] * data["graph"]
            )
            r = data["result"]
            r.score = combined
            r.score_breakdown = ScoreBreakdown(
                keyword=data["keyword"],
                semantic=data["semantic"],
                graph=data["graph"],
            )
            final.append(r)

        return sorted(final, key=lambda x: x.score, reverse=True)
