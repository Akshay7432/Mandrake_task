from pybiomart import Server
import google.generativeai as genai
import pandas as pd
from bioservices import BioMart as biomart

def get_dataset_go(user_query):
    server = Server(host='http://plants.ensembl.org')
    mart = server['plants_mart']
    genai.configure(api_key="GEMINI_API_KEY")

    schema1 = {
        "type": "object",
        "properties": {
            "ensembl_dataset": {"type": "string"},
        },
        "required": ["ensembl_dataset"]
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash-latest"
    )

    response1 = model.generate_content(
        contents=f'''Given the user input: {user_query}, extract the following as a JSON object:\n
            {{
              "ensembl_dataset": "<Ensembl Plants BioMart dataset name for this species from {list(mart.list_datasets()['name'])}>",\n
            }}\n
            Reply ONLY with the JSON.''',
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema1,
        }
    )

    dataset = eval(response1.text)["ensembl_dataset"]

    schema2 = {
        "type": "object",
        "properties": {
            "go": {"type": "string"},
        },
        "required": ["go"]
    }

    response2 = model.generate_content(
        contents=f'''Given the user input: {user_query}, extract the following as a JSON object:\n
            {{
              "go": "<go_id for {user_query}>",\n
            }}\n
            Reply ONLY with the JSON.''',
        generation_config={
            "response_mime_type": "application/json",
            "response_schema": schema2,
        }
    )

    go = eval(response2.text)["go"]

    return(dataset,go)

def get_genes(dataset,go):
    s = biomart('plants.ensembl.org')
    services = [x for x in s.registry()]
    pd.DataFrame(services)
    filt = 'go'
    s.new_query()
    s.add_dataset_to_xml(dataset)
    s.add_filter_to_xml(filt, value = go)
    s.add_attribute_to_xml('ensembl_gene_id')
    s.add_attribute_to_xml('external_gene_name')
    s.add_attribute_to_xml('description')
    #s.add_attribute_to_xml('go_id')
    xmlq = s.get_xml()
    xmlq = xmlq.replace('virtualSchemaName = "default"',\
        'virtualSchemaName = "plants_mart"')
    res = s.query(xmlq)
    genes = [i.split('\t')[0] for i in res.split('\n') if i!='']
    return genes

def genes_to_markdown(genes):
    md_lines = ["### Genes Related to Trait"]
    for gene_id, url in genes:
        md_lines.append(f"| {gene_id} | {url} |")
    return "\n".join(md_lines)

def agent(user_query):
    dataset,go = get_dataset_go(user_query)
    genes = get_genes(dataset,go)
    if len(genes)>5:
        genes = genes[:5]
    for i in range(len(genes)):
        url = f"https://rest.ensembl.org/lookup/id/{genes[i]}?content-type=application/json"
        response = requests.get(url, headers={"Content-Type": "application/json"})
        gene = response.json()
        genes[i] = (genes[i],f"https://plants.ensembl.org/{gene['species']}/Gene/Summary?g={gene['id']}")
    return(genes_to_markdown(genes))

user_query = "drought tolerance in rice"
print(agent(user_query))

