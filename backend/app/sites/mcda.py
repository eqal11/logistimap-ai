"""Pure deterministic MCDA. No spatial values are fabricated here."""
import math
import numpy as np
from app.sites.catalog import CATALOG
class SiteError(ValueError):pass
RI={1:0,2:0,3:.58,4:.90,5:1.12,6:1.24,7:1.32,8:1.41}
def normalize(weights):
 if not weights or any(not math.isfinite(v) or v<0 for v in weights.values()) or sum(weights.values())<=0:raise SiteError("Weights must be finite, nonnegative and have positive total")
 total=sum(weights.values());return {k:v/total for k,v in weights.items()}
def ahp(matrix):
 n=len(matrix)
 if not 1<=n<=8 or any(len(r)!=n for r in matrix):raise SiteError("AHP requires a square matrix of order 1–8")
 a=np.array(matrix,dtype=float)
 if not np.isfinite(a).all() or (a<1/9-1e-10).any() or (a>9+1e-10).any() or not np.allclose(np.diag(a),1,atol=1e-8) or not np.allclose(a*a.T,1,atol=1e-6):raise SiteError("AHP requires unit diagonal, reciprocal entries and Saaty scale 1/9–9")
 vals,vecs=np.linalg.eig(a);index=int(np.argmax(vals.real));weights=np.abs(vecs[:,index].real);weights/=weights.sum()
 lam=float(np.mean(a@weights/weights));ci=max(0.,(lam-n)/(n-1)) if n>1 else 0.;cr=ci/RI[n] if n>2 else 0.
 return {"weights":weights.tolist(),"lambda_max":lam,"ci":ci,"ri":RI[n],"cr":cr,"consistent":cr<=.1,"threshold":.1,"method":"Principal right eigenvector; Saaty RI table for n<=8"}
def evaluate_mcda(s,values):
 ids=[p.id for p in s.candidates];criteria=[c.id for c in s.criteria];warning=[]
 info=ahp(s.ahp_matrix or []) if s.method=="ahp" else None
 if info and len(info["weights"])!=len(criteria):raise SiteError("AHP matrix order must equal selected criteria count")
 if info and not info["consistent"] and not s.allow_inconsistent:raise SiteError("AHP consistency ratio exceeds 0.10; revise matrix or explicitly accept inconsistent judgments")
 if info and not info["consistent"]:warning.append("User explicitly accepted inconsistent AHP judgments; ranking requires caution.")
 weights=normalize(dict(zip(criteria,info["weights"])) if info else {c.id:c.weight for c in s.criteria})
 missing=[(i,k) for i in ids for k in criteria if values.get(i,{}).get(k,{}).get("value") is None]
 if missing and s.missing_policy=="reject":raise SiteError("Missing/unavailable values: "+", ".join(i+"/"+k for i,k in missing)+". Prepare criteria first or choose an explicit missing-value policy.")
 excluded_criteria=sorted({k for _,k in missing}) if s.missing_policy=="exclude_criterion" else []
 excluded_candidates=sorted({i for i,_ in missing}) if s.missing_policy=="exclude_candidate" else []
 active=[k for k in criteria if k not in excluded_criteria];eligible=[i for i in ids if i not in excluded_candidates]
 if not eligible:raise SiteError("No complete candidates remain")
 weights=normalize({k:weights[k] for k in active})
 if missing:warning.append("No imputation: globally excluded criteria/candidates are listed and retained weights renormalized.")
 normalized={i:{} for i in eligible};ranges={}
 for k in active:
  raw=[float(values[i][k]["value"]) for i in eligible]
  if any(not math.isfinite(v) for v in raw):raise SiteError("Criterion values must be finite")
  lo,hi=min(raw),max(raw);direction=next(c.direction for c in s.criteria if c.id==k)
  ranges[k]={"min":lo,"max":hi,"constant":hi==lo,"direction":direction,"unit":CATALOG[k][1]}
  for i,v in zip(eligible,raw):normalized[i][k]=.5 if hi==lo else (v-lo)/(hi-lo) if direction=="benefit" else (hi-v)/(hi-lo)
 def rank(w):
  rows=[{"candidate_id":i,"score":100*sum(normalized[i][k]*w[k] for k in active),
         "contributions":{k:100*normalized[i][k]*w[k] for k in active},"normalized":normalized[i]} for i in eligible]
  rows.sort(key=lambda r:(-round(r["score"],10),r["candidate_id"]))
  # Equal scores share rank; stable IDs only determine display order.
  for row in rows:row["rank"]=1+sum(r["score"]>row["score"]+1e-9 for r in rows)
  return rows
 rows=rank(weights);runs=[]
 for k in active:
  for sign in (-1,1):
   varied=normalize({c:w*(1+sign*s.sensitivity_delta) if c==k else w for c,w in weights.items()})
   ranked=rank(varied)
   runs.append({"criterion":k,"factor":1+sign*s.sensitivity_delta,"weights":varied,"rankings":ranked,
                "top_candidate_ids":[r["candidate_id"] for r in ranked if r["rank"]==1],
                "rank_changes":{r["candidate_id"]:r["rank"]-next(x["rank"] for x in rows if x["candidate_id"]==r["candidate_id"]) for r in ranked}})
 sensitivity=[{"candidate_id":r["candidate_id"],"min_score":min([r["score"]]+[x["score"] for run in runs for x in run["rankings"] if x["candidate_id"]==r["candidate_id"]]),
               "max_score":max([r["score"]]+[x["score"] for run in runs for x in run["rankings"] if x["candidate_id"]==r["candidate_id"]]),
               "min_rank":min([r["rank"]]+[x["rank"] for run in runs for x in run["rankings"] if x["candidate_id"]==r["candidate_id"]]),
               "max_rank":max([r["rank"]]+[x["rank"] for run in runs for x in run["rankings"] if x["candidate_id"]==r["candidate_id"]])} for r in rows]
 return {"rankings":rows,"weights":weights,"ranges":ranges,"ahp":info,"excluded_criteria":excluded_criteria,
         "excluded_candidates":excluded_candidates,"warnings":warning,"sensitivity":{"delta":s.sensitivity_delta,"runs":runs,"summary":sensitivity},
         "methodology":"WLC on observed candidate-set min/max, benefit=(x-min)/(max-min), cost=(max-x)/(max-min); constant criterion=0.5. AHP supplies weights only. No raster interpolation."}
