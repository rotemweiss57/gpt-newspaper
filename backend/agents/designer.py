import os

class DesignerAgent:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def load_html_template(self):
        relative_path = "../templates/index.html"
        dir_path = os.path.dirname(os.path.realpath(__file__))
        html_file_path = os.path.join(dir_path, relative_path)
        with open(html_file_path) as f:
            html_template = f.read()
        return html_template

    def designer(self, email):
        html_template = self.load_html_template()
        # image = email["image"]
        content = email["content"]
        # html_template = html_template.replace("{{image}}", image)
        html_template = html_template.replace("{{content}}", content)
        email["html"] = html_template
        return email

    def run(self, email: dict):
        email = self.designer(email)
        return email
