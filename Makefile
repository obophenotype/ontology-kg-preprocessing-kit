all:
	echo "nothing"

okpk:
	python ontology-kg-preprocessing-kit.py ontology-kg-preprocessing-kit-config.yaml
	
count:
	robot query --use-graphs true -f csv -i build/hp/hp.owl --query build/hp/hp_count_ap.sparql build/hp/hp_count_ap.csv
	
