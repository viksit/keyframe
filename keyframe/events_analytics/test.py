from pyspark import SparkContext

sc = SparkContext(appName = "simple app")

sc._jsc.hadoopConfiguration().set("fs.s3n.awsAccessKeyId", "AKIAJXSES3NWHCU7TNIQ")
sc._jsc.hadoopConfiguration().set("fs.s3n.awsSecretAccessKey", "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")

text_file = sc.textFile("s3n://ml-users/nishant/tmp/myrabot_additional_data.tar.gz")

counts = text_file.flatMap(lambda line: line.split(" ")) \
             .map(lambda word: (word, 1)) \
             .reduceByKey(lambda a, b: a + b)
print counts

#counts.saveAsTextFile("output")

