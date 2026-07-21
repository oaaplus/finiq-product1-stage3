import streamlit as st,pandas as pd
from pathlib import Path
df=pd.read_csv(Path(__file__).parent/"data/raw_events.csv",parse_dates=["event_time"]);df["journey_id"]="JRN-"+df.customer_ref
rules={"INSTRUCTION_RECEIVED":("VALIDATED",30),"VALIDATED":("SWIFT_SENT",60),"SWIFT_SENT":("SETTLEMENT_OBSERVED",360),"SETTLEMENT_OBSERVED":("BENEFICIARY_CONFIRMED",180),"BENEFICIARY_CONFIRMED":("CLOSED",120)}
L=[];S=[]
for jid,g in df.groupby("journey_id"):
 g=g.sort_values("event_time");life=[];tr=0;direct=False
 for _,r in g.iterrows():
  life.append([r.event_time,"OBSERVED",r.event_code,"", ""])
  if r.event_code in rules:
   nxt,m=rules[r.event_code];dl=r.event_time+pd.Timedelta(minutes=m);cand=g[(g.event_code==nxt)&(g.event_time>=r.event_time)];obs=cand.event_time.min() if len(cand) else pd.NaT
   sp=g[(g.event_code=="SUSPENSE_POSTED")&(g.event_time>=r.event_time)];spt=sp.event_time.min() if len(sp) else pd.NaT
   life.append([r.event_time,"EXPECTATION_CREATED",nxt,f"Deadline {dl}",""])
   if not pd.isna(spt) and spt<dl and (pd.isna(obs) or spt<obs):
    direct=True;life.append([spt,"DIRECT_TO_SUSPENSE",nxt,f"{dl-spt} remaining on active expectation",""]);continue
   if pd.isna(obs): tr+=1;life.append([dl,"TRIGGER_RAISED",nxt,"Not observed by deadline",f"T{tr}"])
   elif obs>dl:
    tr+=1;tid=f"T{tr}";life += [[dl,"TRIGGER_RAISED",nxt,"Not observed by deadline",tid],[obs,"TRIGGER_RESOLVED",nxt,"Late evidence observed",tid],[obs,"MONITORING_RESUMED",nxt,"Continue monitoring from observed event",tid]]
   else: life.append([obs,"EXPECTATION_SATISFIED",nxt,"Observed within window",""])
 for x in life:L.append(x+[jid])
 closed=(g.event_code=="CLOSED").any();state="DIRECT_TO_SUSPENSE" if direct else ("COMPLETED_WITH_TRIGGERS" if closed and tr else ("COMPLETED" if closed else "TRIGGERED"))
 S.append([jid,g.amount.max(),g.currency.iloc[0],tr,state])
life=pd.DataFrame(L,columns=["time","lifecycle_state","action_or_expectation","detail","trigger_id","journey_id"]).sort_values("time")
summary=pd.DataFrame(S,columns=["journey_id","amount","currency","trigger_count","current_state"])
st.set_page_config(page_title="FinIQ Product 1 Stage 3",layout="wide");st.title("FinIQ Product 1 — Stateful Journey Monitoring");st.caption("STAGE 3 • trigger → resolution → continuation derived from raw synthetic events")
p=st.sidebar.radio("Navigation",["Control Room","Journey Explorer","Trigger Lifecycle","Direct-to-Suspense"])
a,b,c,d=st.columns(4);a.metric("Journeys",len(summary));b.metric("Completed",(summary.current_state=="COMPLETED").sum());c.metric("Completed with Triggers",(summary.current_state=="COMPLETED_WITH_TRIGGERS").sum());d.metric("Direct-to-Suspense",(summary.current_state=="DIRECT_TO_SUSPENSE").sum())
if p=="Control Room":st.dataframe(summary,use_container_width=True,hide_index=True);st.info("Trigger history is preserved while current state continues through resolution to completion.")
elif p=="Journey Explorer":
 j=st.selectbox("Journey",summary.journey_id.tolist());st.subheader("Source Evidence");st.dataframe(df[df.journey_id==j].sort_values("event_time"),use_container_width=True,hide_index=True);st.subheader("FinIQ Stateful Lifecycle");st.dataframe(life[life.journey_id==j],use_container_width=True,hide_index=True)
elif p=="Trigger Lifecycle":
 j=st.selectbox("Triggered journey",summary[summary.trigger_count>0].journey_id.tolist());st.subheader("Trigger → Resolution → Continuation");st.dataframe(life[(life.journey_id==j)&life.lifecycle_state.isin(["EXPECTATION_CREATED","TRIGGER_RAISED","TRIGGER_RESOLVED","MONITORING_RESUMED","EXPECTATION_SATISFIED"])],use_container_width=True,hide_index=True)
else:
 ds=summary[summary.current_state=="DIRECT_TO_SUSPENSE"];j=st.selectbox("Direct-to-Suspense journey",ds.journey_id.tolist());x=life[life.journey_id==j];st.dataframe(x,use_container_width=True,hide_index=True);h=x[x.lifecycle_state=="DIRECT_TO_SUSPENSE"].iloc[0];st.error(f"Unexpected suspense while waiting for {h.action_or_expectation}. {h.detail}. Evidence trail preserved.")
st.caption("Synthetic test environment • timing windows are not bank SLAs • Product 2 out of scope")
