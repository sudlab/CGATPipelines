from RnaseqDiffExpressionReport import *


class TagCountsCorrelations(ProjectTracker):
    pattern = "(.*)_correlation"

    def __call__(self, track):
        return self.getDict("SELECT * FROM %(track)s_correlation")


class TagCountsSummaryAll(ProjectTracker):
    pattern = "(.*)counts_stats"

    def __call__(self, track):
        return self.getAll("SELECT * FROM %(track)scounts_stats")


class TagCountsSummaryPerDesign(ProjectTracker):
    pattern = "design(.*)_stats"

    def __call__(self, track):
        return self.getAll("SELECT * FROM design%(track)s_stats")


class FeatureCountsSummary(ProjectTracker, SingleTableTrackerRows):
    table = "featurecounts_summary"
