.. _sequence_context:

=======================
Sequence context biases
=======================

The following presents the analysis of potential biasing
factors. Library preparation and sequencing technologies are known to
show biases against particular sequence contexts. For example,
illumina sequencing is biased against regions of extreme GC content. The
aim of this analysis is to establish whether the biases are consistent
between samples and particularly between groups of samples (e.g
different conditions)

Genes/transcripts were binned according to their value for each
potential biasing factor (e.g GC content), with each bin containing an
equal number of genes/transcripts.  The mean expression for the
genes/transcripts within each bin is calculated for each sample. This
mean expression is plotted below, along with a local (loess)
regression for each sample. The expectation is that the fit for each
individual sample will be very similar.


The good

.. report:: GoodExample.Tracker
   :render: myRenderer
   :transform: myTransform
   :options: myAesthetics

   Add a comment about the good example.  What represents good data?

The bad

.. report:: BadExample.Tracker
   :render: myRenderer
   :transform: myTransform
   :options: myAesthetics

   Add a comment about the bad example.  What is specifically bad about this example

More bad examples `<http://myBadData.html >`

Your data:

.. report:: RnaseqqcReport.BiasFactors
   :render: table


Sequencing biases
=================

.. report:: RnaseqqcReport.BiasFactors
   :render: r-ggplot
   :statement: aes(y=as.numeric(value), x=bin, colour=factor_value)+
	       geom_point()+
	       stat_smooth(aes(group=sample_id, colour=factor_value),
	                       method=loess, se=F)+
	       scale_y_continuous(limits=c(0,1))+
	       xlab('')+
	       ylab('Normalised Expression(Nominal scale)')+
	       ggtitle("GC content") +
	       theme(
	       axis.text.x=element_text(size=10,angle=90),
	       axis.text.y=element_text(size=15),
	       title=element_text(size=15),
	       legend.text=element_text(size=15)) +
	       facet_wrap(~factor)

   Mean expression across binned factor levels. Local regression.



Commentary
  This will take the form of some active comments.  This will require the report to
  be published so that it is hosted on the CGAT server/ comments on the DISQUS server.

