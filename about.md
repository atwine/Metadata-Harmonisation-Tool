# About This Tool

This is the Metadata Harmonisation Tool. It helps you map variables from different studies to a common codebook.

The tool is built using [Streamlit](https://streamlit.io/), [Ollama](https://ollama.com/), and [DuckDB](https://duckdb.org/).

### The Role of Ollama (Local AI)

This tool uses a local **Ollama** instance to power its core AI features. For the tool to function correctly, **Ollama must be installed and running on your computer** with the required models downloaded (`nomic-embed-text` and `llama3.1:8b`).

**How it Works:**

1.  **Embedding Generation:** During the `Initialise` step, Ollama creates vector embeddings (numerical representations) of your variable descriptions. The tool compares these embeddings to recommend the most likely mappings between your study and the target codebook.
2.  **Description & Transformation Suggestions:** The AI also assists by generating variable descriptions where they are missing and suggesting potential data transformations, making the mapping process faster and more accurate.

**Why Local AI is Important:**

*   **Privacy:** All data processing happens on your machine. No sensitive or confidential information is ever sent to an external server.
*   **No API Keys or Costs:** You do not need an internet connection or expensive API keys to use the AI features.
*   **Control:** You have full control over the models you use.

---

### How to Navigate This App

Welcome to the Metadata Harmonisation Tool! Here is a quick guide to get you started.

**Use the sidebar on the left to navigate between pages.** Each page corresponds to a step in the mapping workflow:

1.  **`Upload Codebook`**: Start here. Upload your target codebook, which defines the standard set of variables you want to map to.

2.  **`Upload Studies`**: Add the datasets you need to harmonise. You can upload multiple studies, and they will be available for mapping.

3.  **`Initialise`**: Once your codebook and studies are uploaded, go to this page to run the AI-powered recommendation engine. This step generates descriptions and suggests mappings.

4.  **`Map Studies`**: This is where the main mapping work happens. Select a study and begin mapping its variables to your codebook, assisted by the AI recommendations.

5.  **`Download Results`**: After you've completed the mapping for a study, you can download the results as a CSV file from this page.
