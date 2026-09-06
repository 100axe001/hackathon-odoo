import { apiGet } from "../client";
import { reportEndpoints } from "../apiEndpoints";

// Expected: { quotes_created, avg_approval_hours, top_product, pipeline_value,
//             by_status: [{status,count,value}],
//             by_rep: [{rep,quotations,value,flagged_lines}],
//             filter_options: {reps: [str], categories: [str]} }
//
// filters is {days, rep, category}; any of them may be omitted.
export async function loadReports(filters = {}) {
  return apiGet(reportEndpoints.summary(filters));
}
