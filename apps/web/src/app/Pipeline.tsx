import { Link } from "react-router-dom";
import { Async } from "../components/States";
import { useApi } from "../lib/http";

type Board = { stages: string[]; cards: { job_id: string; title: string; stage: string; bid_usd?: number; connects?: number }[] };

/** Kanban: drafted, submitted, viewed, replied, interview, hired, lost. Cards move on marketplace events. */
export default function Pipeline() {
  const { data, loading, error } = useApi<Board>("/pipeline", 6000);
  return (
    <>
      <h1>Pipeline</h1>
      <Async loading={loading} error={error} empty={data?.cards.length === 0 && "Nothing in the pipeline yet. Approve a proposal to start."}>
        <div className="kanban">
          {data?.stages.map((stage) => (
            <section key={stage} aria-label={stage}>
              <h2>{stage} <span className="muted">{data.cards.filter((c) => c.stage === stage).length}</span></h2>
              {data.cards.filter((c) => c.stage === stage).map((c) => (
                <Link key={c.job_id} to={`/studio/${c.job_id}`} className="card small">
                  <b>{c.title}</b>
                  <span className="muted">{c.bid_usd ? `$${c.bid_usd}` : ""} {c.connects ? `· ${c.connects} Connects` : ""}</span>
                </Link>
              ))}
            </section>
          ))}
        </div>
      </Async>
    </>
  );
}
