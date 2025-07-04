# Data Harmonisation Tool

This is a [streamlit](https://streamlit.io) application we have constructed that facilitates the matching of variable names in a dataset to that of a target codebook. The first and often most tedious step in developing a common data model. 

![GUI screenshot](new_demo.gif)

## What it does:

The Metadata Harmonisation Interface provides a convenient portal to match variables from an incoming dataset to a target set of ontologies. In this way the tool provides a similar role to that of the [White Rabbit tool](https://github.com/OHDSI/WhiteRabbit) utilised by the OHDSI community. This tool differentiates itself by using Large Language Models to generate variable descriptions where none have been provided, recommending the most likely target variable to map to as well as supporting creation and testing of variable transformation instructions. A confidence indication is provided alongside mapping recommendations. This dramatically speeds up the mapping process.

## How to use it: 

### Ollama Setup (Required)

This application now uses [Ollama](https://ollama.ai/) for all AI functionality. Before running the tool, you'll need to:

1. **Install Ollama**:
   - Download and install from [ollama.ai](https://ollama.ai/)
   - Ensure Ollama is running (you should see the Ollama icon in your system tray)
   - Ollama runs a local server on port 11434 by default

2. **Download Required Models**:
   - The tool requires two specific models:
     - `llama3.1:8b` for chat functionality (text generation)
     - `nomic-embed-text` for text embeddings
   - Install these models using the following commands in your terminal:
   ```bash
   ollama pull llama3.1:8b
   ollama pull nomic-embed-text
   ```

3. **Verify Models**:
   - Ensure both models are successfully downloaded by running:
   ```bash
   ollama list
   ```
   - You should see both models listed in the output

### Docker (coming soon)

Docker support is coming soon. For now, please use the conda environment setup below.

### Configure python environment

Alternatively if you are familiar with configuring python environments a suitable environment can be configured using conda. 

If you do not have a preferred python package manager already installed I recommend installing [Micromamba](https://mamba.readthedocs.io/en/latest/micromamba-installation.html#)

```
git clone https://github.com/atwine/Metadata-Harmonisation-Tool.git

cd Metadata-Harmonisation-Tool

conda env create -f environment.yml
conda activate harmonisation_env

pip install -r requirements.txt # some packages not available on conda channels

# Make sure Ollama is running and models are downloaded
# See "Ollama Setup" section above

cd app/

streamlit run app.py
```

## Troubleshooting

### Ollama Connection Issues

If you encounter issues connecting to Ollama:

1. **Check if Ollama is running**:
   - Verify the Ollama application is running on your system
   - Check that it's accessible at `http://localhost:11434`

2. **Verify model availability**:
   - Run `ollama list` to confirm required models are downloaded
   - Models should include `llama3.1:8b` and `nomic-embed-text`
   - Note: Model names may have version suffixes (like `:latest`), which is handled automatically

3. **Connection errors**:
   - Ensure no firewall or antivirus software is blocking the connection
   - Restart Ollama if connection fails
   - Check application logs for specific error messages

4. **Model loading errors**:
   - If models appear installed but fail to load, try:
    ```bash
    ollama pull llama3.1:8b --force
    ollama pull nomic-embed-text --force
    ```
    - This will redownload the models if they're corrupted

Please note the application requires a Unix like filesystem and so windows users will need to use WSL. 

## General work flow:

#### Step 1: Upload Target Codebook

This platform is built to harmonise incoming datasets to a single set of target_variables (codebook). An example codebook is included by default. A new codebook can be uploaded under the `Upload Codebook` tab. New codebooks should be in `.csv` format and contain two columns `variable_name` and `description`. It is recommended (but not need for this tool) that these variables be linked to standardised ontologies. 

#### Step 2: Upload Incoming Datasets

From here incoming study data whichs need to be mapped to the target codebook can be uploaded. The following documents can be uploaded: 

 - Study Name (required)
 - Study Description (optional)
 - Variables Table (required)
    - File Format: .csv
    - File Contains: variable names or descriptions from the incoming dataset
    - 2 columns with headers: variable_name, description
  - Example_data (optional)
    - File Format: .csv
    - column headers should correspond to variable name in the dataset variables table.
  - Contextual Documents (optional)
    - File Format: .pdf
    - If the uploaded variables table contains missing variable descriptions a large language model will be used to populate the descriptions. Uploading a study protocol or some other relevant documentation can help inhance this process. 

#### Step 3: Initialise Tool

Once studies have been uploaded, you can run the variable description completion and ontology recommendation engines. This tool uses a local Ollama instance to power its AI features, so please ensure Ollama is installed and running on your machine before you proceed. You will be given the option to fine-tune the LLM prompt used by the description completion engine.

#### Step 3: Map Datasets to Codebook

Once step 1 & 2 have been completed a recommendations algorithm will suggest the most likely variable mappings for each added dataset. The user will be presented with an interface to select the correct mappings from a list of suggested mappings. Thus the actual mapping process remains manual. 

#### Step 4: Download Mapping Results

Once the mapping process has been completed. Each study that has been fully mapped will be available for download as a .csv file. The mapping result is simply a table mapping each dataset variable name to a corresponding codebook variable name. 


## How it works:
The Metadata Harmonisation Interface compromises of two key parts:

First the LLM-based description generator provides a way to quickly and easily extract variable description information from complex free text documents such as study protocols or journal articles. While in an ideal world descriptions should come from a codebook and should match to standardised ontologies, in our experience this is often not the case. The description generator works by taking in a PDF document and converting it to plain text using the pdfminer python package. Next, we use a text-splitter from the Llangchain suite of python functions.  This works by recursively  splitting the text by the special characters: "\n\n", "\n", " ” and "” until a text length of 1000 characters is reached. An overlap of 20 character between chunks is preserved to ensure no information is lost between chunks. A text embedding model is then used to get a vector representation of each chunk. This information is stored as a simple Numpy array.  Next a prompt is constructed by taking an already completed variable and description pair and retrieving the most relevant context, calculated as the spatial distance between the chunk embeddings and the variable name embedding. A hard coded variable and description pair alongside the least relevant context is also included with a (?) appended to the description. This is an attempt to get the LLM to return some indication of whether the context has been useful. If no context is provided by the user a similar prompt pattern is followed without providing the LLM with context. 

The next step in the process is the ontology recommendation engine. This again uses text embeddings to retrieve vector representations of variable names and descriptions for both the target codebook and incoming datasets. Recommendations are then calculated using the spatial distance between vectors weighted 80/20 to descriptions. The interface utilises DuckDB to retrieve these recommendations from plain csv files. 


This work is licensed under a
[Creative Commons Attribution-ShareAlike 4.0 International License][cc-by-sa].  [![CC BY-SA 4.0][cc-by-sa-image]][cc-by-sa]

[cc-by-sa]: http://creativecommons.org/licenses/by-sa/4.0/
[cc-by-sa-image]: https://licensebuttons.net/l/by-sa/4.0/88x31.png
[cc-by-sa-shield]: https://img.shields.io/badge/License-CC%20BY--SA%204.0-lightgrey.svg
