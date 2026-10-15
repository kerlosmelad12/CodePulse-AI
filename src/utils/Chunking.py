import os

terminal = [
    'if_statement',
    'while_statement',
    'for_statement',
    'for_range_loop',
]
ignore_types = {
    "comment",
    "punctuation",
    "identifier",
    "string_literal",
    "block" 
}



def get_nodes_file_paths(project_path,nodes:list[dict]):

    node_labels=['rationale','code']

    paths_nodes = [os.path.join(project_path,node['source_file']) 
                   for node 
                   in nodes if node.get('file_type') in node_labels]

    return paths_nodes

def load_single_file(file_path:str):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return file_path, f.read()
    except Exception as e:
        return file_path , file_path.strip().split("/")[-1]


def extract_subtree(sub_tree):
    subtree_nodes=[]
    queue=[sub_tree]  
    while queue:
        current_node=queue.pop(0)
        for child in current_node.childern:
            child_type=str(child.type)
            if child_type not in ignore_types:
                queue.append(child)
            if child_type in terminal:
                subtree_nodes.append(child)
    return subtree_nodes


def extract_subtrees(root, terminal, ignore_types):
    all_subtrees = []
    queue = [root]
    
    while queue:
        current_node = queue.pop(0)
        current_node_type = str(current_node.type)
        
        if current_node_type in ignore_types:
            continue         
        if current_node_type in terminal:
            all_subtrees.append(current_node)
        else:

            if hasattr(current_node, 'children'):
                queue.extend(current_node.children)
                
    return all_subtrees


