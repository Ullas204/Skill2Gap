export interface FairnessMetricDetail {
  value: number;
  description: string;
  status: string;
}

export interface FairnessMetrics {
  statistical_parity_difference: FairnessMetricDetail;
  disparate_impact_ratio: FairnessMetricDetail;
  equal_opportunity_difference: FairnessMetricDetail;
  demographic_parity: FairnessMetricDetail;
  consistency_score: FairnessMetricDetail;
  composite_fairness_score: FairnessMetricDetail;
  data_points: number;
}

export interface BiasAlert {
  type: string;
  severity: string;
  message: string;
  recommendation: string;
  job_id?: string;
}

export interface FairnessOverview {
  overall_fairness_score: number;
  total_screened: number;
  total_rankings: number;
  total_jobs: number;
  total_candidates: number;
  bias_alerts: BiasAlert[];
  diversity_indicators: {
    total_profiles_analyzed: number;
    gender_distribution: Record<string, number>;
    gender_diversity_index: number;
    location_distribution: Record<string, number>;
    location_diversity_index: number;
  };
  compliance_status: string;
  last_analyzed: string;
}

export interface FairnessReport {
  job_id: string;
  job_title: string;
  total_candidates: number;
  fairness_score: number;
  metrics: Record<string, number>;
  score_distribution: {
    average: number;
    min: number;
    max: number;
    median: number;
    std_dev: number;
  };
  gender_distribution: {
    counts: Record<string, number>;
    percentages: Record<string, number>;
  };
  location_distribution: Record<string, number>;
  bias_alerts: BiasAlert[];
  recommendations: string[];
  trend: Array<{ period: string; fairness_score: number }>;
  hiring_recommendations: Array<{
    area: string;
    recommendation: string;
    priority: string;
  }>;
}

export interface AdversarialVariant {
  variant_type: string;
  original_value: string;
  modified_value: string;
  original_score: number;
  modified_score: number;
  score_difference: number;
  bias_detected: boolean;
}

export interface AdversarialTestResult {
  job_id: string;
  candidate_id: string;
  candidate_name: string;
  original_score: number;
  total_variants_tested: number;
  biased_variants_detected: number;
  stability_score: number;
  bias_sensitivity: string;
  variants: AdversarialVariant[];
  recommendation: string;
}

export interface JDAnalysis {
  job_id: string;
  job_title: string;
  word_count: number;
  bias_score: number;
  ats_compatibility_score: number;
  readability_score: number;
  diversity_score: number;
  gendered_language: Array<{ term: string; gender: string; suggestion: string }>;
  age_biased_language: Array<{ term: string; suggestion: string }>;
  discriminatory_terms: Array<{ term: string; suggestion: string }>;
  exclusive_language: Array<{ term: string; suggestion: string }>;
  unnecessary_requirements: Array<{ term: string; suggestion: string }>;
  total_issues: number;
  inclusive_suggestions: Array<{
    category: string;
    suggestion: string;
    priority: string;
  }>;
  overall_assessment: string;
}

export interface CandidateFairness {
  candidate_id: string;
  candidate_name: string;
  fairness_status: string;
  bias_checks_completed: boolean;
  total_evaluations: number;
  average_score: number;
  transparency_summary: string[];
  protected_attributes_used: string[];
  appeal_available: boolean;
  appeal_status: string;
  last_evaluation_date: string | null;
}
