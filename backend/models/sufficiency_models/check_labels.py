import json
f = open('models/sufficiency_models/data/sufficiency_train.jsonl')
labels = []
for line in f:
    obj = json.loads(line)
    labels.append(obj['label'])
f.close()
print('Total:', len(labels))
print('0.0:', labels.count(0.0))
print('1.0:', labels.count(1.0))