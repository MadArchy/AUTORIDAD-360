import React from 'react';
import { CheckCircle2, Circle } from 'lucide-react';

/**
 * Home del ciclo editorial: qué toca ahora.
 */
export default function HoyTab({
  steps,
  progress,
  nextStep,
  onGo,
}) {
  return (
    <section className="hoy-panel glass-panel">
      <header className="hoy-hero">
        <h2 className="hoy-title">Qué toca ahora</h2>
        <p className="hoy-lede">
          Elige una noticia, genera el formato y publica.
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
    </section>
  );
}
