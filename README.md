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

## Setup

The pipeline is designed to be run as a docker container. To set it up, follow these steps (you have to have docker installed):

1. Download the docker wrapper script (okpk.sh)
2. Provide a configuration file (okpk-example-config.yaml) in the same directory as the above script
3. You should now be able to run the pipeline as follows:

```
sh okpk.sh okpk-example-config.yaml
```