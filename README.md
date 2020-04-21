# Ontology Knowledge Graph Preprocessing Kit (OKPK)

Ontologies are sets of, often complex, axioms that often do not immediately map to `Labelled Property Graphs (LPG)`. Furthermore, they often contain a large amount of knowledge that are not of relevance to a particular use case. Importing such ontologies naively, using tools such as OBO or RDF format parsers that transform the ontology into graph-like structures often leads to the ingestion of a (often huge!) number of relations that do no matter to LPG use case at hand. Furthermore, a potentially large number of valuable relationships are buried deeply in complex axioms (implicit knowledge and complex class expressions), which leads to loss of relevant relationships.

The Ontology Knowledge Graph Preprocessing Kit (OKPK) is a ontology preprocessing pipeline that transforms a set of ontologies into formats more amenable to ingestion into knowledge graphs. It follows the assumption that the majority of use cases are interested in the `relational graph` that is implied by an ontology. There have been a number of attempts to provide a [canonical  definition](https://github.com/cmungall/owlstar) of `relational graph` *of an OWL ontology* (see also [here](https://protegeproject.github.io/owl2lpg/) for a nice overview). In the absence of a shared definition, we define it, for the purpose of the OKPK pipeline, as follows. The relational graph of on OWL ontology is the set of implied axioms of the following forms:

1. A subClassOf B
2. A equivalentTo B
3. A subClassOf R some B

including any annotations pertaining to A, R and B.

The OKPK pipeline works as follows:

1. Downloading the source ontologies
2. Enriching the ontologies by injecting configurable role chains and materialising them
3. Removing any relationships from the ontology not relevant to the use case (configurable)
4. Reducing the ontology to a set of concepts (nodes/classes) of interest (configurable), including
	 1. All their relationships to other concepts
	 2. All annotations of interest (configurable)
5. Exporting the ontology into graph friendly formats
	 1. JSON (obographs)
	 2. KGX spreadsheets

We will discuss these steps in more depth in the following.

## Detailed breakdown of pipeline workings



## Example configuration

### Configuration file breakdown

| Parameter | Explanation |
| --------- | ----------- |
| robot_opts | Global parameters that can be passed to the robot command, such as -vvv |
| clean | true or false: if true, build directories are wiped prior to build. |
| curie_map | Key value pairs of ID to IRI prefix. These are used to automatically generate CURIE style rendering of ids for CSV output formats. |
| global | A set of global configurations that apply to all ontologies in the pipeline. |
| relations | A list of relations that should be considered by the pipeline. All other relationships are removed. |
| annotations | A list of annotation properties that will be considered by the pipeline. All other relationships are removed. |
| ontologies | A list of ontologies that will be preprocessed by the pipeline. |
| id | In the context of an ontology, this is the ontology id, like go, hp, obi. In the context of a term, this is the CURIE denoting the term. |
| sources | A list of a ontology URLs that together constitute the ontology |
| roots | A map of terms in the ontology that define the root notes that will be be considered for export. Overall, OKPK will import the root, all its children an all terms related directly to those terms. |
| chains | A list of role chains that is materialised by the OKPK pipeline. |
| materialize | A boolean flag to say whether OKPK should materialize the relation listed. |

### Example file

```
robot_opts: -vv
clean: false
curie_map:
  RO: http://purl.obolibrary.org/obo/RO_
  HP: http://purl.obolibrary.org/obo/HP_
  BFO: http://purl.obolibrary.org/obo/BFO_
  UPHENO: http://purl.obolibrary.org/obo/UPHENO_
  oio: http://www.geneontology.org/formats/oboInOwl#
  IAO: http://purl.obolibrary.org/obo/IAO_
  dce: http://purl.org/dc/elements/1.1/
global:
  relations: []
  annotations:
    - id: rdfs:label
    - id: skos:exactMatch
    - id: oio:hasExactSynonym
    - id: IAO:0000115
ontologies:
  - id: hp
    sources: 
      - http://purl.obolibrary.org/obo/hp.owl
    roots:
      - id: HP:0000118
        biolink: biolink:PhenotypicFeature
    relations:
      - id: UPHENO:0000001
        biolink: biolink:DiseaseOrPhenotypicFeatureAssociationToThingAssociation
        materialize: true
        chains:
          - BFO:0000051|RO:0000052
      - id: BFO:0000051
        materialize: true
  - id: mondo
    sources: 
      - http://purl.obolibrary.org/obo/mondo.owl
  - id: go
    sources: 
      - http://purl.obolibrary.org/obo/go/go-plus.owl
```

## Setup

The pipeline is designed to be run as a docker container. To set it up, follow these steps (you have to have docker installed):

1. Download the docker wrapper script ([okpk.sh](https://github.com/obophenotype/ontology-kg-preprocessing-kit/blob/master/okpk.sh))
2. Provide a configuration file ([okpk-example-config.yaml](https://github.com/obophenotype/ontology-kg-preprocessing-kit/blob/master/okpk-example-config.yaml)) in the same directory as the above script
3. You should now be able to run the pipeline as follows:

An example repository including a fully configured Jenkins job can be found here:
https://github.com/obophenotype/covid-kg-ontology-preprocessing

```
sh okpk.sh okpk-example-config.yaml
```

## Editors notes:

The okpk is currently build automatically using docker-hub + GitHub integration:
https://hub.docker.com/repository/docker/matentzn/okpk/builds

