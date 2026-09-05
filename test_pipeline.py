#!/usr/bin/env python3
"""
IP-SAKTI Comprehensive Test Suite
Tests the entire ingestion pipeline with timing and progress tracking.
"""

import asyncio
import time
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from ip_sakti.config.loader import reload_settings, get_settings
from ip_sakti.ingestion.pipeline import create_ingestion_pipeline, IngestionJob, IngestionStatus, DocumentType
from ip_sakti.core.models import JurisdictionCode, AuthorityTier
from ip_sakti.retrieval.retrieval_engine import create_retrieval_engine, RetrievalConfig, RetrievalStrategy, SearchRequest, VectorStoreType
from ip_sakti.ingestion.chunking import RecursiveChunker, FixedSizeChunker, ChunkingConfig, ChunkingStrategyType


class Timer:
    """Context manager for timing operations with progress tracking."""
    
    def __init__(self, name: str, verbose: bool = True):
        self.name = name
        self.verbose = verbose
        self.start_time = 0
        self.end_time = 0
        self.iterations = 0
        
    def __enter__(self):
        self.start_time = time.perf_counter()
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"⏱️  Starting: {self.name}")
            print(f"{'='*60}")
        return self
    
    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        elapsed = self.end_time - self.start_time
        if self.verbose:
            print(f"\n✅ Completed: {self.name}")
            print(f"⏱️  Time: {elapsed:.4f}s ({elapsed*1000:.2f}ms)")
            if self.iterations > 0:
                print(f"📊 Iterations: {self.iterations}, Avg: {elapsed/self.iterations*1000:.2f}ms/iter")
            print(f"{'='*60}\n")
    
    def tick(self):
        """Increment iteration counter."""
        self.iterations += 1
        if self.iterations % 100 == 0 and self.verbose:
            elapsed = time.perf_counter() - self.start_time
            print(f"  ... {self.iterations} iterations ({elapsed:.2f}s elapsed)")


async def test_chunking_strategies():
    """Test all chunking strategies with timing."""
    print("\n" + "="*60)
    print("🧪 TESTING CHUNKING STRATEGIES")
    print("="*60)
    
    # Load test document
    doc_path = Path("/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/data/corpus/ip_india/acts/patents_act_1970.txt")
    with open(doc_path, 'r') as f:
        text = f.read()
    
    print(f"📄 Document: {doc_path.name}")
    print(f"📏 Length: {len(text):,} characters")
    
    strategies = [
        ("Recursive (LangChain)", ChunkingStrategyType.RECURSIVE),
        ("Fixed Size", ChunkingStrategyType.FIXED_SIZE),
    ]
    
    for name, strategy_type in strategies:
        with Timer(f"Chunking: {name}") as timer:
            config = ChunkingConfig(
                chunk_size=512,
                chunk_overlap=50,
                min_chunk_size=100,
                strategy=strategy_type,
            )
            
            if strategy_type == ChunkingStrategyType.RECURSIVE:
                chunker = RecursiveChunker(config)
            else:
                chunker = FixedSizeChunker(config)
            
            chunks = await chunker.chunk(text, {'document_id': 'test'})
            timer.iterations = len(chunks)
            
        print(f"📦 Chunks created: {len(chunks)}")
        if chunks:
            avg_size = sum(len(c.content) for c in chunks) / len(chunks)
            print(f"📏 Avg chunk size: {avg_size:.0f} chars")


async def test_ingestion_pipeline():
    """Test the full ingestion pipeline with timing."""
    print("\n" + "="*60)
    print("🧪 TESTING INGESTION PIPELINE")
    print("="*60)
    
    doc_path = Path("/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/data/corpus/ip_india/acts/patents_act_1970.txt")
    
    with Timer("Full Ingestion Pipeline") as timer:
        reload_settings()
        settings = get_settings()
        
        pipeline = create_ingestion_pipeline()
        job = IngestionJob(
            id='perf_test_job',
            source_path=str(doc_path),
            title='Patents Act 1970',
            document_type=DocumentType.ACT,
            jurisdiction=JurisdictionCode.INDIA,
            authority_tier=AuthorityTier.TIER_1,
            metadata={},
            status=IngestionStatus.PENDING,
        )
        
        result = await pipeline.ingest(job)
        timer.iterations = len(result.chunks) if result.chunks else 0
    
    print(f"📋 Status: {result.status}")
    print(f"🆔 Document ID: {result.document_id}")
    print(f"📦 Chunks: {timer.iterations}")
    if result.error_message:
        print(f"❌ Error: {result.error_message}")
    
    return result


async def test_retrieval_engine(chunks):
    """Test the retrieval engine with timing."""
    print("\n" + "="*60)
    print("🧪 TESTING RETRIEVAL ENGINE")
    print("="*60)
    
    with Timer("Retrieval Engine Setup & Indexing") as timer:
        config = RetrievalConfig(
            vector_store=VectorStoreType.IN_MEMORY,
            top_k=10,
        )
        
        engine = create_retrieval_engine(config)
        await engine.initialize()
        await engine.index_chunks(chunks)
        timer.iterations = len(chunks)
    
    print(f"📚 Indexed {len(chunks)} chunks")
    
    # Test queries
    test_queries = [
        "What is Section 3(d) of the Patents Act?",
        "patent claims requirements",
        "copyright amendment act 1999",
        "invention patentability criteria",
        "compulsory licensing provisions",
    ]
    
    print("\n🔍 Running search queries...")
    for query in test_queries:
        with Timer(f"Search: '{query[:40]}...'") as timer:
            search_request = SearchRequest(
                query=query,
                strategy=RetrievalStrategy.HYBRID,
                top_k=5,
            )
            response = await engine.search(search_request)
            timer.iterations = response.total_hits
        
        print(f"  ⏱️  {response.took_ms:.2f}ms | Hits: {response.total_hits}")
        if response.results:
            print(f"  🏆 Top score: {response.results[0].score:.4f}")
            print(f"  📝 Preview: {response.results[0].chunk.content[:80]}...")


async def test_batch_ingestion():
    """Test batch ingestion of multiple documents."""
    print("\n" + "="*60)
    print("🧪 TESTING BATCH INGESTION")
    print("="*60)
    
    data_dir = Path("/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/data/corpus/ip_india/acts")
    files = list(data_dir.glob("*.txt"))[:5]  # Test with first 5 files
    
    print(f"📁 Found {len(files)} documents to ingest")
    
    with Timer("Batch Ingestion") as timer:
        reload_settings()
        pipeline = create_ingestion_pipeline()
        
        results = []
        for i, file_path in enumerate(files):
            job = IngestionJob(
                id=f'batch_job_{i}',
                source_path=str(file_path),
                title=file_path.stem,
                document_type=DocumentType.ACT,
                jurisdiction=JurisdictionCode.INDIA,
                authority_tier=AuthorityTier.TIER_1,
                metadata={},
                status=IngestionStatus.PENDING,
            )
            result = await pipeline.ingest(job)
            results.append(result)
            timer.tick()
            print(f"  ✓ {file_path.name}: {result.status} ({len(result.chunks) if result.chunks else 0} chunks)")
    
    total_chunks = sum(len(r.chunks) for r in results if r.chunks)
    print(f"\n📊 Total: {len(results)} documents, {total_chunks} chunks")


async def test_performance_benchmark():
    """Run performance benchmarks."""
    print("\n" + "="*60)
    print("🧪 PERFORMANCE BENCHMARK")
    print("="*60)
    
    doc_path = Path("/mnt/c/Users/vvars/OneDrive/Desktop/sih rag/data/corpus/ip_india/acts/patents_act_1970.txt")
    with open(doc_path, 'r') as f:
        text = f.read()
    
    # Benchmark chunking
    config = ChunkingConfig(chunk_size=512, chunk_overlap=50, min_chunk_size=100)
    chunker = RecursiveChunker(config)
    
    iterations = 10
    with Timer(f"Chunking Benchmark ({iterations} runs)") as timer:
        for i in range(iterations):
            chunks = await chunker.chunk(text, {'document_id': f'bench_{i}'})
            timer.tick()
    
    avg_time = (timer.end_time - timer.start_time) / iterations * 1000
    print(f"📊 Avg chunking time: {avg_time:.2f}ms per run")
    print(f"📦 Chunks per run: {len(chunks)}")


async def main():
    """Main test runner."""
    print("="*60)
    print("🚀 IP-SAKTI COMPREHENSIVE TEST SUITE")
    print("="*60)
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📁 Working dir: {Path.cwd()}")
    
    try:
        # Test 1: Chunking strategies
        await test_chunking_strategies()
        
        # Test 2: Full ingestion pipeline
        ingestion_result = await test_ingestion_pipeline()
        
        # Test 3: Retrieval engine
        if ingestion_result.chunks:
            await test_retrieval_engine(ingestion_result.chunks)
        
        # Test 4: Batch ingestion
        await test_batch_ingestion()
        
        # Test 5: Performance benchmark
        await test_performance_benchmark()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS COMPLETED SUCCESSFULLY")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())