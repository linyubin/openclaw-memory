#!/usr/bin/env python3
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 初始化向量化器
vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')

text1 = "代码执行规则 所有代码生成任务必须使用Gemini CLI执行"
text2 = "代码生成规则 涉及代码生成、调试的工作必须优先使用Gemini CLI，不得使用其他模型"
text3 = "天气查询规则 用户查询天气时使用wttr.in接口"

# 测试中文文本
print("测试中文文本相似度：")
print(f"文本1: {text1}")
print(f"文本2: {text2}")
print(f"文本3: {text3}")

# 拟合和转换
tfidf_matrix = vectorizer.fit_transform([text1, text2, text3])
print(f"\n词汇表: {vectorizer.get_feature_names_out()}")

sim1_2 = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
sim1_3 = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[2:3])[0][0]
sim2_3 = cosine_similarity(tfidf_matrix[1:2], tfidf_matrix[2:3])[0][0]

print(f"\n文本1和文本2相似度: {sim1_2:.4f}")
print(f"文本1和文本3相似度: {sim1_3:.4f}")
print(f"文本2和文本3相似度: {sim2_3:.4f}")

# 使用中文分词
print("\n\n使用中文分词测试：")
import jieba

def tokenize_chinese(text):
    return list(jieba.cut(text))

vectorizer_cn = TfidfVectorizer(tokenizer=tokenize_chinese, ngram_range=(1, 2))
tfidf_matrix_cn = vectorizer_cn.fit_transform([text1, text2, text3])
print(f"词汇表: {vectorizer_cn.get_feature_names_out()}")

sim1_2_cn = cosine_similarity(tfidf_matrix_cn[0:1], tfidf_matrix_cn[1:2])[0][0]
sim1_3_cn = cosine_similarity(tfidf_matrix_cn[0:1], tfidf_matrix_cn[2:3])[0][0]
sim2_3_cn = cosine_similarity(tfidf_matrix_cn[1:2], tfidf_matrix_cn[2:3])[0][0]

print(f"\n文本1和文本2相似度: {sim1_2_cn:.4f}")
print(f"文本1和文本3相似度: {sim1_3_cn:.4f}")
print(f"文本2和文本3相似度: {sim2_3_cn:.4f}")
