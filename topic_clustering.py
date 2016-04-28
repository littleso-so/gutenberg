from pyspark.mllib.clustering import KMeans, KMeansModel
from pyspark.mllib.linalg import SparseVector
from pyspark import SparkConf, SparkContext
from os.path import join
from pyspark.mllib.util import MLUtils
from pyspark.mllib.feature import StandardScaler
from pyspark.mllib.linalg import Vectors
import pandas as pd
import csv
import sys

"""
make a matrix:    cols words, rows Books
to run:
/Users/jamesledoux/spark-1.6.1/bin/spark-submit  /Users/jamesledoux/Documents/BigData/gutenberg/topic_clustering.py  /Users/jamesledoux/Documents/BigData/gutenberg/
to open the pyspark console
/Users/jamesledoux/spark-1.6.1/bin/pyspark
"""
if(len(sys.argv) != 2):
    print "usage: /sparkPath/bin/spark-submit  name.py  wordDirectory"

conf = SparkConf().setAppName("KMeans TF-IDF").set("spark.executor.memory", "7g")
HomeDir = sys.argv[1]   # passed as argument
#HomeDir = "/Users/jamesledoux/Documents/Big\ Data/movielens/medium/"
#HomeDir = "/Users/jamesledoux/Documents/BigData/gutenberg copy/"
sc = SparkContext()
#SparkContext.setSystemProperty('spark.executor.memory', '4g')


def parseWords(line):
    #uid::wordID::rating::timestamp
    parts = line.strip().split(",")
    return long(1000), (int(parts[0]), int(parts[1]), float(parts[2]))

def loadRows(sc, HomeDir):
    #path = "reformat_output_drew.txt"
    path = "tfidf-scores.csv"
    return sc.textFile(join(HomeDir, path)).map(parseWords)

def vectorize(rows, numWords):
    return rows.map(lambda x: (x[0], (x[1], x[2]))).groupByKey().mapValues(lambda x: SparseVector(numWords, x))

rows = loadRows(sc, HomeDir)
print "type of rows obj: ", type(rows)
print "count of rows: ", rows.count()
print "sample rating: ", rows.take(1)

#rows RDD:  (time stamp, (uid, mid, rows) )
#num of Books  (userid, wordID, rows)
numBooks = rows.values().map(lambda x: x[0]).max()+1
numWords = rows.values().map(lambda x: x[1]).max()+1

# ntransform into sparse vectors
"""
represent as sparse vector to save on space
three cols: id, vector size, wordId:TfIdfscore dictionary
size needed so u know how many zeros are in the sparse matrix
uid, size of vector, (wordid:score, wordid:score, wordid:score))
"""

wordsSparseVector = vectorize( rows.values(), numWords)
#scaler = StandardScaler(withMean = False, withStd = True).fit(features)  #becomes dense if using withMean. may run out of memory locally

#train the model
k = 14
print "training model with " + str(k) + " clusters. . ."
model = KMeans.train(wordsSparseVector.values(), k, maxIterations = 20, runs = 10)

"""
for some reason this goes for all even ids then for all odds.. Should we sort this before writing
to a csv, or is it fine to leave it unordered?
"""
#book = wordsSparseVector.values().take(1)[0] #take a sample of 1 from the data set (use test data when doing this)
books = wordsSparseVector.collect() #book[i][0] == id, book[i][1] == sparse matrix of words:scores
clusterDict = {}
for i in books:
    label = model.predict(i[1])
    clusterDict[i[0]] = label
    print "book id " + str(i[0]) + " predicted as a member of cluster "  + str(label)


other_data = pd.read_csv("/Users/jamesledoux/Documents/gutenberg/output.txt", sep='|')  #this will probably be called something else for you guys. I had too many things named output earlier
other_data['cluster_membership'] = -9999
for key, value in clusterDict.items():
    other_data.loc[other_data.ID == key, 'cluster_membership'] = value
other_data.to_csv('final_data.csv')

sc.stop()
