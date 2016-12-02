from __future__ import print_function
from dsl.doc import DocType
from dsl.field import Text

class Article(DocType):
    title = Text()
    body = Text()

    class Meta:
        index = 'blog'



# This is something
Article.init()
print(Article.__dict__)
article = Article(meta={'id': 42}, title='Hello world!')
article.body = ''' looong text '''
article.save()
print(article.__dict__)
