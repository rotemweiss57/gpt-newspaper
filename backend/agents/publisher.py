import os


class PublisherAgent:
    def __init__(self, output_dir):
        self.output_dir = output_dir

    def save_newspaper_html(self, newspaper_html):
        path = os.path.join(self.output_dir, "newspaper.html")
        with open(path, 'w') as file:
            file.write(newspaper_html)
        return path

    def run(self, newspaper_html: str):
        newspaper_path = self.save_newspaper_html(newspaper_html)
        return newspaper_path
