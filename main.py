import arxiv
import openai
import time
import itertools
import os
import argparse

# Set language
parser = argparse.ArgumentParser()
parser.add_argument('--language', type=str, default='jp')
parser.add_argument('--show-range', type=int, default=10)
args = parser.parse_args()

language = args.language
show_range = args.show_range

# Const
with open("./key/key.txt", 'r', encoding='utf-8') as file: 
    api_key = file.read().strip()
with open("./prompts/translator.txt", 'r', encoding='utf-8') as file: 
    translator_prompt = file.read().strip()
with open("./prompts/reader.txt", 'r', encoding='utf-8') as file: 
    reader_prompt = file.read().strip()

lan_dict = {'en': 'English', 'cn': 'Chinese', 'jp': 'Japanese'}
properties = ["entry_id", "updated", "published", "authors", "comment", 
              "journal_ref", "doi", "primary_category", "categories", "links"]
log_path = './logs'
paper_path = './papers'
seed = 3407

assert language in lan_dict.keys(), f"Language '{language}' is not supported. "

# Construct the default API client.
axv = arxiv.Client()
gpt = openai.OpenAI(api_key=api_key)

# Prepare paper reader
vector_store = gpt.beta.vector_stores.create(name='papers')
reader = gpt.beta.assistants.create(
    name="paper_reader",
    instructions=reader_prompt.format(language=lan_dict[language]),
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vector_store.id]}}, 
    model="gpt-4o",
)


def translate(titles):
    translation = gpt.chat.completions.create(
        model="gpt-4o",
        temperature=0.2, 
        seed=seed, 
        messages=[
            {"role": "system", "content": translator_prompt.format(language=lan_dict[language])},
            {"role": "user", "content": titles}
        ]
    )
    return translation.choices[0].message.content.strip() + '\n'

def read_paper(paper): 
    title = paper.title
    file_path = os.path.join(log_path, f"{title}.txt")

    # Title and Abstract
    contents = ''
    for info in ['title', 'summary']: 
        tmp = paper.__dict__[info].replace('\n', ' ') + '\n\n'
        if language != 'en': 
            tmp += translate(tmp) + '\n'
        contents += tmp

    # Other info
    for k, v in paper.__dict__.items(): 
        if k in properties:
            contents += f"{k}: {v}\n"
    contents += '\n\n'

    # Load paper
    paper.download_pdf(dirpath=paper_path, filename=f"{title}.pdf")
    paper_file = gpt.files.create(
        file=open(os.path.join(paper_path, f"{title}.pdf"), "rb"),
        purpose="assistants"
    )
    gpt.beta.vector_stores.files.create(
        vector_store_id=vector_store.id,
        file_id=paper_file.id
    )
    run = gpt.beta.threads.create_and_run(assistant_id=reader.id)

    return file_path, contents, run.thread_id, run.id, paper_file.id

def delete_all():
    global results
    del results
    gpt.beta.assistants.delete(reader.id)
    gpt.beta.vector_stores.delete(vector_store_id=vector_store.id)


query = input("Please enter your query: ")

# Start to search
search = arxiv.Search(
    query = query,
    sort_by = arxiv.SortCriterion.SubmittedDate
)
results = axv.results(search)

round = 0
while True: 
    print(f"\nRound {round + 1}: {round * show_range + 1} ~ {(round + 1) * show_range}")
    round += 1
    batch = list(itertools.islice(results, show_range))
    if not batch:
        print("All data processed. ")
        break
    
    # Get titles
    original_titles = ''
    for i, data in enumerate(batch): 
        original_titles += f"[ {i+1} ]\t{data.title}\n"
    print(original_titles)
    if language != 'en':
        print("Translated: ")
        print(translate(original_titles))

    # Choose papers
    selected_idx = input("Enter index(es) of paper for more info (press enter to skip or 'q' to quit): ").strip()
    if selected_idx == 'q': 
        delete_all()
        break
    if selected_idx == '':
        continue 
    selected_idx = list(map(eval, selected_idx.split()))
    cache = {}
    for j, i in enumerate(selected_idx): 
        assert i > 0 and i <= show_range
        print(f"\rPreparing for read ... ({j+1} / {len(selected_idx)})", end='', flush=True)
        idx = i - 1
        current_paper = batch[idx]
        cur = read_paper(current_paper)
        cache[i] = cur
    print("\rPreparing for read ... Finished! ")

    # Read each paper
    for k, v in cache.items(): 
        fp, ct, tid, rid, fid = v
        count = 0
        while True:
            run = gpt.beta.threads.runs.retrieve(thread_id=tid, run_id=rid)
            print(f"\rReading paper[{k}] ... {count}", end='', flush=True)

            if run.status == "completed": 
                messages = gpt.beta.threads.messages.list(thread_id=tid)
                for message in messages: 
                    ct += message.content[0].text.value
                with open(fp, 'w', encoding='utf-8') as file: 
                    file.write(ct)
                print(f"\rReading paper[{k}] ... Completed! ")
                break

            if run.status == "failed": 
                print(f"\rReading paper [{k}] ... Failed. ")
                break
            count += 1
            time.sleep(1)

        gpt.beta.vector_stores.files.delete(
            vector_store_id=vector_store.id,
            file_id=fid
        )
        gpt.files.delete(fid)


    key = input("Continue? (press enter to continue or 'q' to quit): ")
    if key == 'q':
        delete_all()
        break
