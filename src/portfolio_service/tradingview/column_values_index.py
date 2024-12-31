from collections import defaultdict
import re

import tradingview_screener.constants


class ColumnIndex:
    def __init__(self, case_sensitive=False):
        self.index = defaultdict(set)
        self.documents = {}
        self.case_sensitive = case_sensitive
        for col_desc, col in tradingview_screener.constants.COLUMNS.items():
            self.add_document(col, col_desc)

    def add_document(self, doc_id, content):
        # Store original content
        self.documents[doc_id] = content

        # Preprocess the content
        if not self.case_sensitive:
            content = content.lower()

        # Split into words and index each word
        words = re.findall(r'\w+', content)
        for word in words:
            self.index[word].add(doc_id)

    def search(self, query):
        if not self.case_sensitive:
            query = query.lower()

        # Split query into words
        query_words = re.findall(r'\w+', query)

        if not query_words:
            return set()

        # Start with documents matching the first word
        results = self.index.get(query_words[0], set())

        # Intersect with documents containing all other words
        for word in query_words[1:]:
            results &= self.index.get(word, set())

        return results

index = ColumnIndex()
