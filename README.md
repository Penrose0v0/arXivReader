# arXivReader
The main purpose of this repo is to simplize the procedure of reading paper in arXiv. 

## Introduction
This project enables users to search for, read, and process academic papers from arXiv directly through a command-line interface. 
The integrated GPT model can translate titles and abstracts, and also summarize the whole paper. 

For more information about arxiv package, read [arxiv.py](https://github.com/lukasschwab/arxiv.py/tree/master) and [the arXiv API](https://arxiv.org/help/api/index). 
For more information about openai package, read [OpenAI API reference](https://platform.openai.com/docs/api-reference/introduction). 

## Installation
Mainly, run: 
```
pip install arxiv
pip install openai
```

## How to use
1. **Enter your API key**: Add `key.txt` in `./key/` where your api key is saved. 
1. **Start the application**: Run `python main.py --language xxx`. Currently, only English, Chinese and Japanese are supported, but you can always modify `lan_dict` in `main.py` to add your own language.
1. **Enter a query**: Type your search keywords. If you want to change your query, you have to finish the current program then start it again. 
1. **Select papers**: Enter the index (for example, `3 7` or `10`) to select papers that you are interested in. GPT will generate summary for each paper you selected. After that, check `./logs/` and read your paper. 