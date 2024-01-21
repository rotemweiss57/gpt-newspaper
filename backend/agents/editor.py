import os


class EditorAgent:

    def load_html_template(self):
        template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'newspaper', 'index.html')
        with open(template_path) as f:
            return f.read()

    def editor(self, articles):
        html_template = self.load_html_template()
        article_template = """
        <div class="article">
            <a href="{{path}}" target="_blank"><h2>{{title}}</h2></a>
            <img src="{{image}}" alt="Article Image">
            <p class="date">{{date}}</p>
            <p>{{summary}}</p>
        </div>
        """
        articles_html = ""
        for article in articles:
            article_html = article_template.replace("{{title}}", article["title"])
            article_html = article_html.replace("{{image}}", article["image"])
            article_html = article_html.replace("{{date}}", article["date"])
            article_html = article_html.replace("{{summary}}", article["summary"])
            article_html = article_html.replace("{{path}}", article["path"])
            articles_html += article_html

        newspaper_html = html_template.replace("{{articles}}", articles_html)
        return newspaper_html

    def run(self, articles):
        res = self.editor(articles)
        return res
