import { apiGet } from "../client";
import { reportEndpoints } from "../apiEndpoints";
import { MOCK_REPORTS } from "../mocks";

// Expected: { quotes_created, avg_approval_hours, top_product, pipeline_value,
//             by_status: [{status,count,value}], by_rep: [{rep,quotations,value,flagged_lines}] }
export async function loadReports() {
  try {
    return await apiGet(reportEndpoints.summary);
  } catch {
    return MOCK_REPORTS;
  }
}
