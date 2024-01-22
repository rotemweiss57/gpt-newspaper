import os

article_templates = {
    "layout_1.html": """
    <div class="article">
        <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
        <img src="{{image}}" alt="Article Image">
        <p>{{summary}}</p>
    </div>
    """,
    "layout_2.html": """
    <div class="article">
        <img src="{{image}}" alt="Article Image">
        <div>
            <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
            <p>{{summary}}</p>
        </div>
    </div>
    """,
    "layout_3.html": """
    <div class="article">
        <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
        <img src="{{image}}" alt="Article Image">
        <p>{{summary}}</p>
    </div>
    """,
}

class EditorAgent:
    def __init__(self, layout):
        self.layout = layout

    def load_html_template(self):
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'newspaper', 'layouts', self.layout)
        with open(template_path) as f:
            return f.read()

    def editor(self, articles):
        html_template = self.load_html_template()

        # Article template
        article_template = article_templates[self.layout]

        # Generate articles HTML
        articles_html = ""
        for article in articles:
            article_html = article_template.replace("{{title}}", article["title"])
            article_html = article_html.replace("{{image}}", article["image"])
            article_html = article_html.replace("{{summary}}", article["summary"])
            article_html = article_html.replace("{{path}}", article["path"])
            articles_html += article_html

        # Replace placeholders in template
        html_template = html_template.replace("{{date}}", articles[0]["date"])
        newspaper_html = html_template.replace("{{articles}}", articles_html)
        return newspaper_html

    def run(self, articles):
        res = self.editor(articles)
        return res
