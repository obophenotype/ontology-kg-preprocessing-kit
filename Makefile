# Building docker image
VERSION = "v0.0.1" 
IM=obolibrary/okpk

docker-build:
	@docker build -t $(IM):$(VERSION) . \
	&& docker tag $(IM):$(VERSION) $(IM):latest
	
docker-build-no-cache:
	@docker build --no-cache -t $(IM):$(VERSION) . \
	&& docker tag $(IM):$(VERSION) $(IM):latest

all:
	echo "nothing"

okpk:
	python ontology-kg-preprocessing-kit.py ontology-kg-preprocessing-kit-config.yaml
	
count:
	robot query --use-graphs true -f csv -i build/hp/hp.owl --query build/hp/hp_count_ap.sparql build/hp/hp_count_ap.csv
	
ncbi:
	robot diff --left-iri ncbitaxon.obo --right build/ncbitaxon.obo -o ncbi_diff.txt