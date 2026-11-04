
from html.parser import HTMLParser
import json


class AccessibilityParser(HTMLParser):

    def __init__(self, filename):
        super().__init__()

        self.filename = filename
        self.issues = []
        self.images = 0
        self.forms = 0
        self.headings = []
        self.labels = set()
        self.used_labels = set()
        self.inputs = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        line = self.getpos()[0]

        if tag == "img":
            self.images += 1

            if "alt" not in attrs:
                self.add_issue(
                    line,
                    "Image is missing an alt attribute"
                )

        if tag == "input":
            self.inputs.append({
                "line": line,
                "id": attrs.get("id"),
                "type": attrs.get("type", "text"),
                "has_aria_label": bool(
                    attrs.get("aria-label")
                    or attrs.get("aria-labelledby")
                )
            })

        if tag == "textarea" or tag == "select":
            self.inputs.append({
                "line": line,
                "id": attrs.get("id"),
                "type": tag,
                "has_aria_label": bool(
                    attrs.get("aria-label")
                    or attrs.get("aria-labelledby")
                )
            })

        if tag == "form":
            self.forms += 1

        if tag == "label" and "for" in attrs:
            self.labels.add(attrs["for"])

        if tag == "h1" or tag == "h2" or tag == "h3":
            self.headings.append({
                "level": int(tag[1]),
                "line": line
            })

        if tag == "a":
            if not attrs.get("href"):
                self.add_issue(
                    line,
                    "Link is missing an href attribute"
                )

    def handle_endtag(self, tag):
        pass

    def add_issue(self, line, message):
        self.issues.append({
            "file": self.filename,
            "line": line,
            "issue": message
        })

    def finish_analysis(self):
        for item in self.inputs:
            field_id = item["id"]

            if (
                not item["has_aria_label"]
                and (not field_id or field_id not in self.labels)
            ):
                self.add_issue(
                    item["line"],
                    "Form field may be missing an accessible label"
                )

        previous_level = 0

        for heading in self.headings:
            current_level = heading["level"]

            if previous_level and current_level > previous_level + 1:
                self.add_issue(
                    heading["line"],
                    "Heading level skipped"
                )

            previous_level = current_level


def analyze_accessibility(files):
    report = {
        "files_analyzed": 0,
        "total_images": 0,
        "total_forms": 0,
        "issues": [],
        "html_errors": []
    }

    for file in files:
        path = file.get("path", "")
        content = file.get("content", "")

        if not path.lower().endswith((".html", ".htm")):
            continue

        parser = AccessibilityParser(path)

        try:
            parser.feed(content)
            parser.close()
            parser.finish_analysis()

            report["files_analyzed"] += 1
            report["total_images"] += parser.images
            report["total_forms"] += parser.forms
            report["issues"].extend(parser.issues)

        except Exception as error:
            report["html_errors"].append({
                "file": path,
                "message": str(error)
            })

    report["total_issues"] = len(report["issues"])

    return report


def print_report(report):
    print("\n===== HTML ACCESSIBILITY REPORT =====")

    print("Files analyzed:", report["files_analyzed"])
    print("Images found:", report["total_images"])
    print("Forms found:", report["total_forms"])
    print("Accessibility issues:", report["total_issues"])

    print("\nDetected Issues:")

    if not report["issues"]:
        print("No issues detected by these checks.")

    for item in report["issues"]:
        print(
            f"- {item['file']}:{item['line']} "
            f"{item['issue']}"
        )

    print("\nHTML Parsing Errors:", len(report["html_errors"]))


def export_report(report, filename="accessibility_report.json"):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)

    print("\nReport exported to", filename)


if __name__ == "__main__":
    sample_files = [
        {
            "path": "index.html",
            "content": '''
<html>
<body>
    <h1>Welcome</h1>
    <h3>About Us</h3>

    <img src="logo.png">

    <form>
        <input type="text" id="username">
        <button>Submit</button>
    </form>

    <a>Learn More</a>
</body>
</html>
'''
        }
    ]

    result = analyze_accessibility(sample_files)
    print_report(result)
    export_report(result)
