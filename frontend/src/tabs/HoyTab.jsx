import React from 'react';
import { ArrowRight, CheckCircle2, Circle } from 'lucide-react';

/**
 * Home del ciclo editorial: qué toca ahora + un CTA.
 */
export default function HoyTab({
  steps,
  progress,
  doneCount,
  nextStep,
  onGo,
}) {
  const active = nextStep || steps[steps.length - 1];
  const allDone = !nextStep;

  return (
    <section className="hoy-panel glass-panel">
      <header className="hoy-hero">
        <h2 className="hoy-title">Qué toca ahora</h2>
        <p className="hoy-lede">
          Elige una noticia → genera formatos → aprueba → publica.
        </p>
      </header>

      <ol className="hoy-steps">
        {steps.map((step, index) => {
          const done = Boolean(progress[step.id]);
          const isNext = nextStep?.id === step.id;
          return (
            <li
              key={step.id}
              className={`hoy-step ${done ? 'is-done' : ''} ${isNext ? 'is-next' : ''}`}
            >
              <button type="button" className="hoy-step-btn" onClick={() => onGo(step.tab)}>
                <span className="hoy-step-mark" aria-hidden="true">
                  {done ? <CheckCircle2 size={18} /> : <Circle size={18} />}
                </span>
                <span className="hoy-step-body">
                  <strong>
                    {index + 1}. {step.label}
                  </strong>
                  <span>{step.hint}</span>
                </span>
              </button>
            </li>
          );
        })}
      </ol>

      <div className="hoy-cta-card">
        {allDone ? (
          <>
            <p className="hoy-cta-kicker">Ciclo completo</p>
            <h3>Buen trabajo — el ciclo de hoy está cerrado</h3>
            <p>Puedes elegir otra noticia o revisar resultados.</p>
            <div className="hoy-cta-actions">
              <button type="button" className="btn btn-primary" onClick={() => onGo('top10')}>
                Elegir otra noticia <ArrowRight size={16} />
              </button>
              <button type="button" className="btn btn-secondary" onClick={() => onGo('publish')}>
                Ver publicaciones
              </button>
            </div>
          </>
        ) : (
          <>
            <p className="hoy-cta-kicker">
              Paso {doneCount + 1} de {steps.length}
            </p>
            <h3>{active.label}</h3>
            <p>{active.hint}</p>
            <button type="button" className="btn btn-primary" onClick={() => onGo(active.tab)}>
              {active.cta || `Ir a ${active.label}`} <ArrowRight size={16} />
            </button>
          </>
        )}
      </div>
    </section>
  );
}
