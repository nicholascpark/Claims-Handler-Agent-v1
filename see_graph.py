"""Standalone script to visualize the LangGraph workflow.

Run this script from the terminal to see the graph diagram.
"""

from voice_langgraph.graph_builder import build_voice_agent_graph
from langchain_core.runnables.graph import MermaidDrawMethod
from PIL import Image
import io
import sys


def show_graph():
    """Generate and display the LangGraph workflow diagram."""
    # Build the graph
    print("Building graph...")
    app = build_voice_agent_graph(with_memory=False)
    
    try:
        # Try local rendering using Pyppeteer (avoids SSL issues with mermaid.ink API)
        print("Generating visualization using local rendering...")
        png_bytes = app.get_graph().draw_mermaid_png(
            draw_method=MermaidDrawMethod.PYPPETEER
        )
    except Exception as e:
        print(f"⚠ Local rendering failed: {e}")
        print("\nFalling back to saving mermaid diagram...")
        
        # Fallback: Save as mermaid file
        mermaid_syntax = app.get_graph().draw_mermaid()
        with open("graph.mmd", "w", encoding="utf-8") as f:
            f.write(mermaid_syntax)
        
        print("✓ Graph saved as 'graph.mmd'")
        print("\nTo visualize:")
        print("  1. Visit https://mermaid.live")
        print("  2. Paste the contents of graph.mmd")
        print("  3. Or install mermaid-cli: npm install -g @mermaid-js/mermaid-cli")
        print("     Then run: mmdc -i graph.mmd -o graph.png")
        return
    
    # Display the image
    try:
        image = Image.open(io.BytesIO(png_bytes))
        image.show()
        print("✓ Graph visualization opened in default image viewer")
    except Exception as e:
        print(f"⚠ Failed to display image: {e}")
        # Save as PNG file as fallback
        with open("graph.png", "wb") as f:
            f.write(png_bytes)
        print("✓ Graph saved as 'graph.png'")


if __name__ == "__main__":
    try:
        show_graph()
    except KeyboardInterrupt:
        print("\n✗ Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
