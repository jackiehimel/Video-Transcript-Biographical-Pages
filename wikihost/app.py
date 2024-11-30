from flask import Flask, render_template
import json
import re

app = Flask(__name__)

# Load all WikiText pages from the JSON file
with open('all_wikipages.json') as f:
    wiki_data = json.load(f)

def parse_wikitext(wikitext):
    """Convert WikiText to HTML-like structure with improved parsing"""
    lines = wikitext.split("\n")
    html = ""
    in_list = False
    sections = {
        'content': [],
        'external_links': [],
        'references': [],
        'categories': []
    }
    current_section = 'content'
    
    # Remove duplicate title if it appears twice
    if len(lines) > 1 and lines[0].strip('= ') == lines[1].strip('= '):
        lines.pop(0)
    
    for line in lines:
        line = line.strip()
        
        # Detect section changes
        if line == "== External Links ==" or line == "= External Links =":
            current_section = 'external_links'
            continue
        elif line == "== References ==" or line == "= References =":
            current_section = 'references'
            continue
        elif line.startswith("[[Category:"):
            category = line.replace("[[Category:", "").replace("]]", "")
            sections['categories'].append(category)
            continue
            
        # Handle main content parsing
        if current_section == 'content':
            # Convert YouTube citations to simple links
            line = re.sub(
                r'\[(.*?)\]\((https://www\.youtube\.com/watch\?v=.*?)\) - Uploaded on [\d-]+',
                r'<a href="\2" target="_blank">\1</a>',
                line
            )
            
            # Handle other external links
            line = re.sub(
                r'\[(.*?)\]\((https?://[^\s)]+)\)',
                r'<a href="\2" target="_blank">\1</a>',
                line
            )
            
            # Handle wiki-style links
            def wiki_link_replacement(match):
                link_text = match.group(1)
                page_exists = link_text in wiki_data
                css_class = "" if page_exists else " class='new'"
                return f'<a href="/topic/{link_text}"{css_class}>{link_text}</a>'
            
            line = re.sub(r'\[\[(.*?)\]\]', wiki_link_replacement, line)
            
            # Handle headings and other content
            if line.startswith("==="):
                sections['content'].append(f'<h3 id="{line.strip("= ").lower().replace(" ", "-")}">{line.strip("= ")}</h3>')
            elif line.startswith("=="):
                sections['content'].append(f'<h2 id="{line.strip("= ").lower().replace(" ", "-")}">{line.strip("= ")}</h2>')
            elif line.startswith("="):
                sections['content'].append(f'<h1 id="{line.strip("= ").lower().replace(" ", "-")}">{line.strip("= ")}</h1>')
            elif line.startswith("*"):
                if not in_list:
                    sections['content'].append("<ul>")
                    in_list = True
                sections['content'].append(f"<li>{line.lstrip('* ')}</li>")
            elif in_list and line:
                sections['content'].append("</ul>")
                in_list = False
                sections['content'].append(f"<p>{line}</p>")
            elif line:
                if in_list:
                    sections['content'].append("</ul>")
                    in_list = False
                sections['content'].append(f"<p>{line}</p>")
        
        # Handle external links section
        elif current_section == 'external_links' and line.startswith("*"):
            link_match = re.match(r'\*\s*\[(.*?)\]\((https?://[^\s)]+)\)', line)
            if link_match:
                text, url = link_match.groups()
                sections['external_links'].append(f'<li><a href="{url}" target="_blank">{text}</a></li>')
    
    if in_list:
        sections['content'].append("</ul>")
    
    # Combine all sections into final HTML
    html = "\n".join(sections['content'])
    
    # Add External Links section if it exists
    if sections['external_links']:
        html += '\n<h2>External Links</h2>\n<ul>\n'
        html += "\n".join(sections['external_links'])
        html += '\n</ul>'
    
    # Add Categories section if it exists
    if sections['categories']:
        html += '\n<div class="categories">'
        for category in sections['categories']:
            html += f'<div class="category"><a href="/category/{category}">Category:{category}</a></div>'
        html += '</div>'
    
    return html

@app.route('/')
def home():
    # Create a clean list of topics with titles and descriptions
    topics = []
    for id, content in wiki_data.items():
        lines = content.split('\n')
        title = lines[0].strip('= ')
        
        # Get first paragraph as description, skipping empty lines and headers
        description = ""
        for line in lines[1:]:
            line = line.strip()
            if line and not line.startswith('=') and not line.startswith('*'):
                # Clean up any [[brackets]] in the description
                description = re.sub(r'\[\[(.*?)\]\]', r'\1', line)
                break
                
        topics.append({
            'id': id,
            'title': title,
            'description': description[:200] + '...' if len(description) > 200 else description
        })
    
    # Sort topics alphabetically by title
    topics.sort(key=lambda x: x['title'])
    
    return render_template('index.html', topics=topics)

@app.route('/topic/<id>')
def topic(id):
    content = wiki_data.get(id, "Topic not found.")
    
    if content == "Topic not found.":
        return render_template('topic.html', 
                             title="Topic Not Found", 
                             content="<p>The requested page does not exist yet.</p>")
    
    # Parse WikiText content into HTML
    parsed_content = parse_wikitext(content)
    
    # Get title from first heading
    title = content.split('\n')[0].strip('=').strip()
    
    return render_template('topic.html', title=title, content=parsed_content)

@app.route('/category/<name>')
def category(name):
    # Find all pages in this category
    category_pages = []
    for id, content in wiki_data.items():
        if f"[[Category:{name}]]" in content:
            title = content.split('\n')[0].strip('= ')
            category_pages.append({
                'id': id,
                'title': title
            })
    
    category_pages.sort(key=lambda x: x['title'])
    
    return render_template('category.html', 
                         category_name=name,
                         pages=category_pages)

if __name__ == '__main__':
    app.run(debug=True)
