FROM obolibrary/odkfull:latest
LABEL maintainer="obo-tools@googlegroups.com" 

COPY ontology-kg-preprocessing-kit.py /tools
COPY lib.py /tools
ENV SPARQLDIR=/tools/sparql
COPY /sparql /tools/sparql

ENV BUILDDIR=/build
RUN mkdir /build

#CMD python /tools/ontology-kg-preprocessing-kit.py 
ENTRYPOINT ["python", "/tools/ontology-kg-preprocessing-kit.py"]