rule compareTargetsToTms:
	input:
		tms= "mappings/" + "nonAnchoredMergeReads/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.gff",
		targetedSegments=config["TARGETSDIR"] + "{capDesign}_primary_targets.exons.reduced.gene_type.segments.gtf"
	output: "mappings/" + "nonAnchoredMergeReads/vsTargets/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.gfftsv.gz"
	shell:
		'''
bedtools intersect -wao -a {input.targetedSegments} -b {input.tms} |gzip > {output}

		'''

rule getTargetCoverageStats:
	input: "mappings/" + "nonAnchoredMergeReads/vsTargets/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.gfftsv.gz"
	output: temp(config["STATSDATADIR"] + "{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.targetCoverage.stats.tsv")
	shell:
		'''
for type in `zcat {input} | extractGffAttributeValue.pl gene_type | sort|uniq`; do
all=$(zcat {input} | fgrep "gene_type \\"$type\\";" | extractGffAttributeValue.pl transcript_id | sort|uniq|wc -l)
detected=$(zcat {input} | fgrep "gene_type \\"$type\\";" | awk '$NF>0' | extractGffAttributeValue.pl transcript_id | sort|uniq|wc -l)
let undetected=$all-$detected || true
echo -e "{wildcards.techname}Corr{wildcards.corrLevel}\t{wildcards.capDesign}\t{wildcards.sizeFrac}\t{wildcards.barcodes}\t$type\t$all\t$detected" | awk '{{print $0"\t"$7/$6}}'
done |sed 's/{wildcards.capDesign}_//' > {output}
		'''

rule aggTargetCoverageStats:
	input: expand(config["STATSDATADIR"] + "{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.targetCoverage.stats.tsv",filtered_product_merge, techname=TECHNAMES, corrLevel=FINALCORRECTIONLEVELS, capDesign=CAPDESIGNS, sizeFrac=SIZEFRACSpluSMERGED, barcodes=BARCODESpluSMERGED)
#lambda wildcards: expand(config["STATSDATADIR"] + "{techname}Corr{corrLevel}_{capDesign}_pooled.targetCoverage.stats.tsv", techname=TECHNAMES, corrLevel=FINALCORRECTIONLEVELS, capDesign=CAPDESIGNS)
	output: config["STATSDATADIR"] + "all.targetCoverage.stats.tsv"
	shell:
		'''
echo -e "seqTech\tcorrectionLevel\tcapDesign\tsizeFrac\ttissue\ttargetType\ttotalTargets\tdetectedTargets\tpercentDetectedTargets" > {output}
cat {input} | grep -v erccSpikein | sed 's/Corr0/\tNo/' | sed 's/Corr{lastK}/\tYes/'| sort >> {output}
		'''

rule plotTargetCoverageStats:
	input: config["STATSDATADIR"] + "all.targetCoverage.stats.tsv"
	output: config["PLOTSDIR"] + "{capDesign}_{byFrac}_{byTissue}.targetCoverage.stats.{ext}"
	params:
		filterDat=lambda wildcards: merge_figures_params(wildcards.capDesign, wildcards.byFrac, wildcards.byTissue)
	shell:
		'''
echo "library(ggplot2)
library(plyr)
library(scales)
dat <- read.table('{input}', header=T, as.is=T, sep='\\t')
{params.filterDat}
plotWidth = plotWidth + 1
plotHeight = plotHeight + 1

ggplot(dat, aes(x=factor(correctionLevel), y=percentDetectedTargets, fill=targetType)) +
geom_bar(width=0.75,stat='identity', position=position_dodge(width=0.9)) +
scale_fill_manual(values={long_Rpalette}) +
 facet_grid( seqTech +sizeFrac ~ capDesign + tissue) +
 geom_hline(aes(yintercept=1), linetype='dashed', alpha=0.7) +
 geom_text(size=geom_textSize, aes(group=targetType, y=0.01, label = paste(sep='',percent(percentDetectedTargets),' / ','(',comma(detectedTargets),')')), angle=90, size=2.5, hjust=0, vjust=0.5, position = position_dodge(width=0.9)) +
 ylab('% targeted regions detected') + xlab('Error correction') + scale_y_continuous(limits = c(0, 1), labels = scales::percent)+
{GGPLOT_PUB_QUALITY}
ggsave('{output}', width=plotWidth, height=plotHeight)
" > {output}.r
cat {output}.r | R --slave


		'''


rule gffcompareToAnnotation:
	input:
		annot=lambda wildcards: CAPDESIGNTOANNOTGTF[wildcards.capDesign],
		tm="mappings/" + "nonAnchoredMergeReads/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.gff"
	output: "mappings/" + "nonAnchoredMergeReads/gffcompare/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.vs.gencode.simple.tsv"
	shell:
		'''
pref=$(basename {output} .simple.tsv)
annotFullPath=$(fullpath {input.annot})
tmFullPath=$(fullpath {input.tm})
cd $(dirname {output})
gffcompare -T -o $pref -r $annotFullPath $tmFullPath
cat $pref.tracking | simplifyGffCompareClasses.pl - > $(basename {output})

		'''

rule getGffCompareStats:
	input: "mappings/" + "nonAnchoredMergeReads/gffcompare/{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.vs.gencode.simple.tsv"
	output: temp(config["STATSDATADIR"] + "{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.vs.gencode.stats.tsv")
	shell:
		'''
cat {input} |cut -f4 | sort|uniq -c | awk -v s={wildcards.techname}Corr{wildcards.corrLevel} -v c={wildcards.capDesign} -v si={wildcards.sizeFrac} -v b={wildcards.barcodes} '{{print s"\t"c"\t"si"\t"b"\t"$2"\t"$1}}' | sed 's/Corr0/\tNo/' | sed 's/Corr{lastK}/\tYes/' |sed 's/{wildcards.capDesign}_//'>> {output}
		'''


#echo -e "seqTech\tcorrectionLevel\tcapDesign\tcategory\tcount" > {output}

rule aggGffCompareStats:
	input: expand(config["STATSDATADIR"] + "{techname}Corr{corrLevel}_{capDesign}_{sizeFrac}_{barcodes}.tmerge.vs.gencode.stats.tsv",filtered_product_merge, techname=TECHNAMES, corrLevel=FINALCORRECTIONLEVELS, capDesign=CAPDESIGNS, sizeFrac=SIZEFRACSpluSMERGED, barcodes=BARCODESpluSMERGED)
	output: config["STATSDATADIR"] + "all.tmerge.vs.gencode.stats.tsv"
	shell:
		'''
echo -e "seqTech\tcorrectionLevel\tcapDesign\tsizeFrac\ttissue\tcategory\tcount" > {output}
cat {input} >> {output}
		'''

rule plotGffCompareStats:
	input: config["STATSDATADIR"] + "all.tmerge.vs.gencode.stats.tsv"
	output: config["PLOTSDIR"] + "{capDesign}_{byFrac}_{byTissue}.tmerge.vs.gencode.stats.{ext}"
	params:
		filterDat=lambda wildcards: merge_figures_params(wildcards.capDesign, wildcards.byFrac, wildcards.byTissue)
	shell:
		'''
echo "library(ggplot2)
library(plyr)
library(scales)
dat <- read.table('{input}', header=T, as.is=T, sep='\\t')
{params.filterDat}
dat\$category<-factor(dat\$category, ordered=TRUE, levels=rev(c('Intergenic', 'Extends', 'Intronic', 'Overlaps', 'Antisense', 'Equal', 'Included')))
palette <- c('Intergenic' = '#0099cc', 'Extends' ='#00bfff', 'Intronic' = '#4dd2ff', 'Overlaps' = '#80dfff', 'Antisense' = '#ccf2ff', 'Equal' = '#c65353', 'Included' ='#d98c8c')

ggplot(dat[order(dat\$category), ], aes(x=factor(correctionLevel), y=count, fill=category)) +
geom_bar(stat='identity') +
scale_fill_manual(values=palette) +
facet_grid( seqTech + sizeFrac ~ capDesign + tissue)+ ylab('# TMs') + xlab('Error correction') + guides(fill = guide_legend(title='Category'))+
scale_y_continuous(labels=scientific)+
{GGPLOT_PUB_QUALITY}
ggsave('{output}', width=plotWidth, height=plotHeight)
" > {output}.r
cat {output}.r | R --slave

		'''

#calculate amount of novel nucleotides
