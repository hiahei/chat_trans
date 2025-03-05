import translators as ts

q_text = '可以翻译一下这一个长长的句子吗'
# q_html = '''<!DOCTYPE html><html><head><title>《季姬击鸡记》</title></head><body><p>还有另一篇文章《施氏食狮史》。</p></body></html>'''

### usage
_ = ts.preaccelerate_and_speedtest()  # Optional. Caching sessions in advance, which can help improve access speed.

print(ts.translators_pool)
print(ts.translate_text(q_text))
# print(ts.translate_html(q_html, translator='alibaba'))

### parameters
# help(ts.translate_text)