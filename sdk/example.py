"""
Comprehensive example demonstrating all ShareBib SDK features

This example demonstrates:
1. Listing existing collections
2. Creating a new collection
3. Adding papers to a collection
4. Listing papers in a collection
5. Getting individual paper details
6. Removing papers from a collection
7. Deleting a collection
"""

from sharebib import ShareBibClient

# Configuration
BASE_URL = "http://localhost:11550"  # Change this to your ShareBib instance URL
API_KEY = "pc_your_api_key_here"  # Replace with your actual API key


def main():
    # Initialize the client
    print("=" * 70)
    print("ShareBib SDK - Comprehensive Example")
    print("=" * 70)

    client = ShareBibClient(base_url=BASE_URL, api_key=API_KEY)

    # ========== 1. List existing collections ==========
    print("\n[1/7] Listing existing collections...")
    collections = client.list_collections()
    print(f"✓ Found {len(collections)} collection(s):")
    for c in collections:
        print(f"  - {c.title} ({c.paper_count} papers, {c.visibility})")

    # ========== 2. Create a new collection ==========
    print("\n[2/7] Creating a new collection...")
    collection = client.create_collection(
        title="SDK Demo Collection",
        description="Comprehensive demo of Paper Collector SDK features",
        visibility="private",  # Options: "private", "public", "public_editable"
        tags=["demo", "sdk", "example"],
    )
    print(f"✓ Created collection: '{collection.title}'")
    print(f"  - ID: {collection.id}")
    print(f"  - Visibility: {collection.visibility}")
    print(f"  - Tags: {', '.join(collection.tags)}")

    # ========== 3. Add multiple papers ==========
    print("\n[3/7] Adding papers to the collection...")

    # Paper 1: With full metadata and links
    paper1 = client.add_paper(
        collection_id=collection.id,
        title="Attention Is All You Need",
        authors=[
            "Ashish Vaswani",
            "Noam Shazeer",
            "Niki Parmar",
            "Jakob Uszkoreit",
            "Llion Jones",
            "Aidan N. Gomez",
            "Lukasz Kaiser",
            "Illia Polosukhin",
        ],
        venue="NeurIPS 2017",
        year=2017,
        abstract=(
            "The dominant sequence transduction models are based on complex "
            "recurrent or convolutional neural networks that include an encoder "
            "and a decoder. The best performing models also connect the encoder "
            "and decoder through an attention mechanism. We propose a new simple "
            "network architecture, the Transformer, based solely on attention "
            "mechanisms, dispensing with recurrence and convolutions entirely."
        ),
        arxiv_id="1706.03762",
        url_arxiv="https://arxiv.org/abs/1706.03762",
        url_pdf="https://arxiv.org/pdf/1706.03762.pdf",
        url_code="https://github.com/tensorflow/tensor2tensor",
        tags=["transformers", "attention", "nlp"],
    )
    print(f"✓ Added paper 1: '{paper1.title}'")
    print(f"  - Status: {paper1.status} (has PDF link)")

    # Paper 2: Minimal metadata, no links
    paper2 = client.add_paper(
        collection_id=collection.id,
        title="BERT: Pre-training of Deep Bidirectional Transformers",
        authors=["Jacob Devlin", "Ming-Wei Chang", "Kenton Lee", "Kristina Toutanova"],
        year=2019,
        tags=["bert", "nlp", "pretraining"],
    )
    print(f"✓ Added paper 2: '{paper2.title}'")
    print(f"  - Status: {paper2.status} (no PDF link)")

    # Paper 3: With DOI
    paper3 = client.add_paper(
        collection_id=collection.id,
        title="GPT-3: Language Models are Few-Shot Learners",
        authors=["Tom B. Brown", "Benjamin Mann", "Nick Ryder"],
        venue="NeurIPS 2020",
        year=2020,
        doi="10.48550/arXiv.2005.14165",
        url_arxiv="https://arxiv.org/abs/2005.14165",
        tags=["gpt", "language-models", "few-shot"],
    )
    print(f"✓ Added paper 3: '{paper3.title}'")

    # ========== 4. List all papers in the collection ==========
    print("\n[4/7] Listing all papers in the collection...")
    papers = client.list_papers(collection.id)
    print(f"✓ Collection contains {len(papers)} paper(s):")
    for i, p in enumerate(papers, 1):
        authors_str = ", ".join(p.authors[:2])
        if len(p.authors) > 2:
            authors_str += f" et al. ({len(p.authors)} authors)"
        print(f"  {i}. {p.title}")
        print(f"     Authors: {authors_str}")
        print(f"     Year: {p.year}, Status: {p.status}")
        if p.tags:
            print(f"     Tags: {', '.join(p.tags)}")

    # ========== 5. Get individual paper details ==========
    print("\n[5/7] Getting details of a specific paper...")
    paper_detail = client.get_paper(paper1.id)
    print(f"✓ Paper: '{paper_detail.title}'")
    print(f"  - ID: {paper_detail.id}")
    print(f"  - Authors: {len(paper_detail.authors)} authors")
    print(f"  - Venue: {paper_detail.venue}")
    print(f"  - Year: {paper_detail.year}")
    print(f"  - arXiv: {paper_detail.arxiv_id}")
    print(f"  - Status: {paper_detail.status}")
    if paper_detail.url_pdf:
        print(f"  - PDF: {paper_detail.url_pdf}")
    if paper_detail.url_code:
        print(f"  - Code: {paper_detail.url_code}")

    # ========== 6. Remove a paper from the collection ==========
    print("\n[6/7] Removing a paper from the collection...")
    print(f"Removing: '{paper2.title}'")
    client.remove_paper(collection.id, paper2.id)
    print("✓ Paper removed")

    # Verify removal
    papers_after_removal = client.list_papers(collection.id)
    print(f"Collection now has {len(papers_after_removal)} paper(s)")

    # ========== 7. Get updated collection info ==========
    print("\n[7/7] Getting updated collection information...")
    updated_collection = client.get_collection(collection.id)
    print(f"✓ Collection: '{updated_collection.title}'")
    print(f"  - Paper count: {updated_collection.paper_count}")
    print(f"  - Visibility: {updated_collection.visibility}")
    print(f"  - Created: {updated_collection.created_at}")
    print(f"  - Updated: {updated_collection.updated_at}")

    # ========== Optional: Delete the collection ==========
    print("\n[Optional] Cleaning up - Delete the demo collection?")
    print("Uncomment the following lines to delete the collection:")
    print(f"# client.delete_collection('{collection.id}')")
    print("# print('✓ Collection deleted')")

    print("\n" + "=" * 70)
    print("✅ All examples completed successfully!")
    print("=" * 70)
    print(f"\nView your collection at: {BASE_URL}/collections/{collection.id}")
    print("\nTo delete this demo collection, run:")
    print(f"  client.delete_collection('{collection.id}')")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure:")
        print("1. Your ShareBib instance is running")
        print("2. You've replaced API_KEY with your actual API key")
        print("3. The BASE_URL is correct")
