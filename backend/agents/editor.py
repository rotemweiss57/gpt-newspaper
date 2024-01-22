import os

class EditorAgent:
    def load_html_template(self):
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'newspaper', 'index.html')
        with open(template_path) as f:
            return f.read()

    def load_css_content(self, layout):
        css_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'newspaper', 'layouts', layout)
        with open(css_path) as f:
            return f.read()

    def editor(self, articles, layout='layout_1.css'):
        html_template = self.load_html_template()
        css_content = self.load_css_content(layout)

        # Insert CSS content into HTML template
        html_template = html_template.replace("<!-- CSS_PLACEHOLDER -->", css_content)

        # Article template
        article_template = """
        <div class="article">
            <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
            <img src="{{image}}" alt="Article Image">
            <p class="date">{{date}}</p>
            <p>{{summary}}</p>
        </div>
        """

        # Generate articles HTML
        articles_html = ""
        for article in articles:
            article_html = article_template.replace("{{title}}", article["title"])
            article_html = article_html.replace("{{image}}", article["image"])
            article_html = article_html.replace("{{date}}", article["date"])
            article_html = article_html.replace("{{summary}}", article["summary"])
            article_html = article_html.replace("{{path}}", article["path"])
            articles_html += article_html

        # Replace placeholders in template
        newspaper_html = html_template.replace("{{articles}}", articles_html)
        return newspaper_html

    def run(self, articles):
        res = self.editor(articles)
        return res
