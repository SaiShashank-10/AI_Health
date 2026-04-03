/**
 * Application Logic — Intake Form, Pipeline Visualization, Results Dashboard
 *
 * Handles:
 *   - Multi-step form navigation with validation
 *   - API calls to the FastAPI backend
 *   - Animated pipeline agent visualization
 *   - Results rendering with expand/collapse cards
 *   - Three.js scene interaction hooks
 */

(function () {
    'use strict';

    // ═══ CONFIG ═══
    const API_BASE = 'http://127.0.0.1:8000/api';

    // ═══ DOM REFERENCES ═══
    const sections = {
        intake: document.getElementById('section-intake'),
        pipeline: document.getElementById('section-pipeline'),
        results: document.getElementById('section-results'),
    };

    const form = document.getElementById('intake-form');
    const btnSubmit = document.getElementById('btn-submit');
    const btnNewSession = document.getElementById('btn-new-session');

    // Pipeline
    const pipelineNodes = document.querySelectorAll('.pipeline-node');
    const pipelineConnectors = document.querySelectorAll('.pipeline-connector');
    const progressFill = document.getElementById('pipeline-progress-fill');
    const progressText = document.getElementById('pipeline-progress-text');

    // Results
    const riskBanner = document.getElementById('risk-banner');
    const riskBadge = document.getElementById('risk-badge');
    const riskLevelText = document.getElementById('risk-level-text');
    const riskTitle = document.getElementById('risk-title');
    const riskJustification = document.getElementById('risk-justification');
    const riskConfidence = document.getElementById('risk-confidence');
    const riskSession = document.getElementById('risk-session');

    // Agent ordering for animation
    const AGENT_ORDER = [
        'normalization',
        'triage',
        'orchestrator',
        'allopathy_specialist',
        'ayurveda_specialist',
        'safety_conflict',
        'recommendation_synthesizer',
        'translation_agent',
    ];

    const AGENT_COLORS = {
        normalization: '#00F5D4',
        triage: '#FF4757',
        orchestrator: '#7B61FF',
        allopathy_specialist: '#00D4FF',
        ayurveda_specialist: '#2ED573',
        safety_conflict: '#FFA502',
        recommendation_synthesizer: '#FF6EC7',
        translation_agent: '#1E90FF',
    };


    // ═══════════════════════════════════════════════════════════════
    //  MULTI-STEP FORM NAVIGATION
    // ═══════════════════════════════════════════════════════════════

    function initFormNavigation() {
        // Next buttons
        document.querySelectorAll('.btn-next').forEach(btn => {
            btn.addEventListener('click', () => {
                const currentStep = parseInt(btn.closest('.form-step').dataset.step);
                if (validateStep(currentStep)) {
                    goToStep(parseInt(btn.dataset.next));
                }
            });
        });

        // Back buttons
        document.querySelectorAll('.btn-prev').forEach(btn => {
            btn.addEventListener('click', () => {
                goToStep(parseInt(btn.dataset.prev));
            });
        });

        // Step dot clicks
        document.querySelectorAll('.step-dot').forEach(dot => {
            dot.addEventListener('click', () => {
                const targetStep = parseInt(dot.dataset.step);
                const currentStep = getCurrentStep();
                // Only allow going back or to completed steps
                if (targetStep <= currentStep) {
                    goToStep(targetStep);
                }
            });
        });

        // Modality checkbox toggle styling
        document.querySelectorAll('.modality-checkbox:not(.disabled)').forEach(label => {
            label.addEventListener('click', () => {
                setTimeout(() => {
                    const input = label.querySelector('input');
                    if (input.checked) {
                        label.classList.add('checked');
                    } else {
                        label.classList.remove('checked');
                    }
                }, 10);
            });
        });
    }

    function getCurrentStep() {
        const active = document.querySelector('.form-step.active');
        return active ? parseInt(active.dataset.step) : 1;
    }

    function goToStep(step) {
        // Update form steps
        document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
        const targetStep = document.querySelector(`.form-step[data-step="${step}"]`);
        if (targetStep) targetStep.classList.add('active');

        // Update step indicators
        document.querySelectorAll('.step-dot').forEach(dot => {
            const dotStep = parseInt(dot.dataset.step);
            dot.classList.remove('active', 'completed');
            if (dotStep === step) {
                dot.classList.add('active');
            } else if (dotStep < step) {
                dot.classList.add('completed');
            }
        });

        // Update step lines
        const lines = document.querySelectorAll('.step-line');
        lines.forEach((line, idx) => {
            if (idx < step - 1) {
                line.classList.add('active');
            } else {
                line.classList.remove('active');
            }
        });
    }

    function validateStep(step) {
        if (step === 1) {
            const age = document.getElementById('inp-age').value;
            const sex = document.getElementById('inp-sex').value;
            if (!age || age < 0 || age > 150) {
                shakeField('inp-age');
                return false;
            }
            if (!sex) {
                shakeField('inp-sex');
                return false;
            }
            return true;
        }
        if (step === 2) {
            const symptoms = document.getElementById('inp-symptoms').value.trim();
            if (!symptoms || symptoms.length < 2) {
                shakeField('inp-symptoms');
                return false;
            }
            return true;
        }
        return true;
    }

    function shakeField(fieldId) {
        const field = document.getElementById(fieldId);
        field.style.borderColor = '#FF4757';
        field.style.animation = 'shake 0.4s ease';
        field.addEventListener('animationend', () => {
            field.style.animation = '';
        }, { once: true });
        // Add shake keyframe dynamically
        if (!document.getElementById('shake-style')) {
            const style = document.createElement('style');
            style.id = 'shake-style';
            style.textContent = `
                @keyframes shake {
                    0%, 100% { transform: translateX(0); }
                    20% { transform: translateX(-6px); }
                    40% { transform: translateX(6px); }
                    60% { transform: translateX(-4px); }
                    80% { transform: translateX(4px); }
                }
            `;
            document.head.appendChild(style);
        }
        setTimeout(() => { field.style.borderColor = ''; }, 1500);
    }


    // ═══════════════════════════════════════════════════════════════
    //  FORM SUBMISSION
    // ═══════════════════════════════════════════════════════════════

    function initFormSubmission() {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            if (!validateStep(4)) return;

            // Gather form data
            const payload = buildPayload();

            // Show pipeline section
            showSection('pipeline');
            resetPipelineUI();

            // Disable submit
            btnSubmit.disabled = true;
            btnSubmit.querySelector('.btn-text').style.display = 'none';
            btnSubmit.querySelector('.btn-loader').style.display = 'inline-block';

            // Trigger 3D effect
            if (window.ThreeScene) {
                window.ThreeScene.boost();
                window.ThreeScene.pulse('#00D4FF', 0.5);
            }

            try {
                // Call API
                const response = await fetch(`${API_BASE}/intake`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    const err = await response.json();
                    throw new Error(err.detail || 'API Error');
                }

                const data = await response.json();
                const sessionId = data.session_id;

                // Animate pipeline nodes
                await animatePipeline(sessionId);

                // Fetch full recommendation
                const recResponse = await fetch(`${API_BASE}/recommendation/${sessionId}`);
                if (!recResponse.ok) throw new Error('Failed to fetch recommendation');

                const recommendation = await recResponse.json();

                // Render results
                renderResults(recommendation);
                showSection('results');

                // 3D celebration
                if (window.ThreeScene) {
                    window.ThreeScene.pulse('#2ED573', 0.7);
                }

                // Show new session button
                btnNewSession.style.display = 'flex';

            } catch (err) {
                console.error('Pipeline error:', err);
                alert(`Error: ${err.message}\n\nMake sure the backend is running on ${API_BASE}`);
                showSection('intake');
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.querySelector('.btn-text').style.display = '';
                btnSubmit.querySelector('.btn-loader').style.display = 'none';
            }
        });
    }

    function buildPayload() {
        const modalities = [];
        document.querySelectorAll('input[name="modality"]:checked').forEach(cb => {
            modalities.push(cb.value);
        });
        if (modalities.length === 0) modalities.push('allopathy');

        const payload = {
            age: parseInt(document.getElementById('inp-age').value),
            sex: document.getElementById('inp-sex').value,
            language_pref: document.getElementById('inp-language').value,
            symptom_text: document.getElementById('inp-symptoms').value.trim(),
            modality_preferences: modalities,
        };

        const duration = document.getElementById('inp-duration').value;
        if (duration) payload.duration_days = parseInt(duration);

        const comorbidities = document.getElementById('inp-comorbidities').value.trim();
        if (comorbidities) {
            payload.comorbidities = comorbidities.split(',').map(s => s.trim()).filter(Boolean);
        }

        const medications = document.getElementById('inp-medications').value.trim();
        if (medications) {
            payload.medications = medications.split(',').map(s => s.trim()).filter(Boolean);
        }

        const allergies = document.getElementById('inp-allergies').value.trim();
        if (allergies) {
            payload.allergies = allergies.split(',').map(s => s.trim()).filter(Boolean);
        }

        const lifestyle = document.getElementById('inp-lifestyle').value.trim();
        if (lifestyle) payload.lifestyle_notes = lifestyle;

        return payload;
    }


    // ═══════════════════════════════════════════════════════════════
    //  PIPELINE ANIMATION
    // ═══════════════════════════════════════════════════════════════

    function resetPipelineUI() {
        pipelineNodes.forEach(node => {
            node.classList.remove('running', 'completed');
            node.querySelector('.node-status').textContent = 'Pending';
        });
        pipelineConnectors.forEach(c => c.classList.remove('active'));
        progressFill.style.width = '0%';
        progressText.textContent = '0 / 8 agents';
    }

    async function animatePipeline(sessionId) {
        for (let i = 0; i < AGENT_ORDER.length; i++) {
            const agentName = AGENT_ORDER[i];
            const node = document.querySelector(`.pipeline-node[data-agent="${agentName}"]`);

            if (node) {
                // Set running
                node.classList.add('running');
                node.querySelector('.node-status').textContent = 'Running...';

                // Pulse 3D scene with agent color
                if (window.ThreeScene) {
                    window.ThreeScene.pulse(AGENT_COLORS[agentName] || '#00F5D4', 0.3);
                }
            }

            // Simulate processing time (staggered for visual effect)
            const delay = 300 + Math.random() * 250;
            await sleep(delay);

            if (node) {
                // Set completed
                node.classList.remove('running');
                node.classList.add('completed');
                node.querySelector('.node-status').textContent = 'Complete ✓';
            }

            // Activate connector
            if (i < pipelineConnectors.length) {
                pipelineConnectors[i].classList.add('active');
            }

            // Update progress
            const progress = ((i + 1) / AGENT_ORDER.length) * 100;
            progressFill.style.width = `${progress}%`;
            progressText.textContent = `${i + 1} / ${AGENT_ORDER.length} agents`;
        }

        // Final pause before results
        await sleep(500);
    }


    // ═══════════════════════════════════════════════════════════════
    //  RESULTS RENDERING
    // ═══════════════════════════════════════════════════════════════

    function renderResults(rec) {
        // Risk Banner
        const riskLevel = rec.risk_level || 'routine';
        riskBadge.className = `risk-badge ${riskLevel}`;
        riskLevelText.textContent = riskLevel.toUpperCase();
        riskTitle.textContent = `Risk Assessment — ${riskLevel.charAt(0).toUpperCase() + riskLevel.slice(1)}`;
        riskJustification.textContent = rec.triage_justification || 'No justification provided.';
        riskConfidence.textContent = `Confidence: ${(rec.risk_confidence * 100).toFixed(0)}%`;
        riskSession.textContent = `Session: ${rec.session_id}`;

        // Care Path
        renderCarePath(rec.care_path || []);

        // Plan Segments
        renderPlanSegments(rec.plan_segments || []);

        // Warnings
        renderWarnings(rec.warnings || []);

        // Evidence
        renderEvidence(rec.provenance || []);

        // Translations
        renderTranslations(rec.translations || []);

        // Explainability
        renderExplainability(rec.explainability || {}, rec.agent_trace || []);
    }

    function renderCarePath(steps) {
        const body = document.getElementById('carepath-body');
        if (steps.length === 0) {
            body.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No care path generated.</p>';
            return;
        }

        let html = '<ul>';
        steps.forEach(step => {
            const icon = step.modality === 'allopathy' ? '🏥' :
                         step.modality === 'ayurveda' ? '🌿' :
                         step.modality === 'homeopathy' ? '💧' : '🏠';
            html += `<li>
                <strong>Step ${step.step_number}:</strong> ${icon} 
                <strong>${step.modality.charAt(0).toUpperCase() + step.modality.slice(1)}</strong> 
                (${step.priority}) → ${step.specialist_type}
                <br><small style="color:var(--text-muted)">${step.reason}</small>
            </li>`;
        });
        html += '</ul>';
        body.innerHTML = html;
    }

    function renderPlanSegments(segments) {
        const body = document.getElementById('plans-body');
        if (segments.length === 0) {
            body.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No treatment plans generated.</p>';
            return;
        }

        let html = '';
        segments.forEach(seg => {
            const icon = seg.modality === 'allopathy' ? '🏥' :
                         seg.modality === 'ayurveda' ? '🌿' : '💊';
            html += `<div class="segment-title">${icon} ${seg.title}</div>`;

            // Recommendations
            if (seg.recommendations && seg.recommendations.length > 0) {
                html += '<ul>';
                seg.recommendations.forEach(rec => {
                    html += `<li>${escapeHtml(rec)}</li>`;
                });
                html += '</ul>';
            }

            // Medications
            if (seg.medications && seg.medications.length > 0) {
                html += '<div class="segment-title" style="font-size:0.8rem;color:var(--accent-cyan)">💊 Medications / Formulations</div>';
                html += '<ul>';
                seg.medications.forEach(med => {
                    html += `<li>${escapeHtml(med)}</li>`;
                });
                html += '</ul>';
            }

            // Lifestyle
            if (seg.lifestyle && seg.lifestyle.length > 0) {
                html += '<div class="segment-title" style="font-size:0.8rem;color:var(--accent-purple)">🧘 Lifestyle</div>';
                html += '<ul>';
                seg.lifestyle.slice(0, 8).forEach(ls => {
                    html += `<li>${escapeHtml(ls)}</li>`;
                });
                html += '</ul>';
            }

            // Follow-up
            if (seg.follow_up) {
                html += `<div style="margin:10px 0;padding:8px 12px;border-radius:6px;background:rgba(0,245,212,0.05);border:1px solid rgba(0,245,212,0.1);font-size:0.8rem;color:var(--text-secondary)">
                    📅 <strong>Follow-up:</strong> ${escapeHtml(seg.follow_up)}
                </div>`;
            }
        });
        body.innerHTML = html;
    }

    function renderWarnings(warnings) {
        const body = document.getElementById('warnings-body');
        if (warnings.length === 0) {
            body.innerHTML = '<p style="color:var(--risk-routine);font-size:0.85rem;">✅ No safety warnings — care plan is clear.</p>';
            return;
        }

        let html = '<ul style="list-style:none;padding:0;">';
        warnings.forEach(w => {
            html += `<li class="warning-item ${w.severity}" style="padding-left:14px;">
                <strong>[${w.severity.toUpperCase()}]</strong> ${escapeHtml(w.message)}
                ${w.resolution ? `<br><small style="color:var(--accent-teal)">💡 ${escapeHtml(w.resolution)}</small>` : ''}
                <br><small style="color:var(--text-muted)">Rule: ${w.rule_id}</small>
            </li>`;
        });
        html += '</ul>';
        body.innerHTML = html;
    }

    function renderEvidence(evidence) {
        const body = document.getElementById('evidence-body');
        if (evidence.length === 0) {
            body.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No evidence sources cited.</p>';
            return;
        }

        let html = '<ul>';
        evidence.forEach(ev => {
            const tierClass = `tier-${ev.reliability_tier}`;
            html += `<li>
                <span class="evidence-tier ${tierClass}">Tier ${ev.reliability_tier}</span>
                <strong>${escapeHtml(ev.title)}</strong>
                <br><small style="color:var(--text-muted)">${escapeHtml(ev.source_type)}${ev.year ? ` (${ev.year})` : ''}</small>
                ${ev.summary ? `<br><small style="color:var(--text-secondary)">${escapeHtml(ev.summary)}</small>` : ''}
            </li>`;
        });
        html += '</ul>';
        body.innerHTML = html;
    }

    function renderTranslations(translations) {
        const body = document.getElementById('translations-body');
        if (translations.length === 0) {
            body.innerHTML = '<p style="color:var(--text-muted);font-size:0.85rem;">No translations available.</p>';
            return;
        }

        let html = '';
        translations.forEach(t => {
            html += `<div class="translation-lang">🌐 ${t.language_name} (${t.language_code})</div>`;
            html += `<div class="translation-summary">${escapeHtml(t.summary)}</div>`;
        });
        body.innerHTML = html;
    }

    function renderExplainability(explain, traces) {
        const body = document.getElementById('explainability-body');
        let html = '';

        // Risk factors
        if (explain.risk_factors && explain.risk_factors.length > 0) {
            html += '<div class="segment-title">🎯 Risk Factors</div><ul>';
            explain.risk_factors.forEach(f => {
                html += `<li>${escapeHtml(f)}</li>`;
            });
            html += '</ul>';
        }

        // Rule triggers
        if (explain.rule_triggers && explain.rule_triggers.length > 0) {
            html += '<div class="segment-title">⚡ Rules Triggered</div><ul>';
            explain.rule_triggers.forEach(r => {
                html += `<li>${escapeHtml(r)}</li>`;
            });
            html += '</ul>';
        }

        // Agent traces
        if (traces.length > 0) {
            html += '<div class="segment-title">📊 Agent Execution Trace</div>';
            traces.forEach(t => {
                html += `<div class="trace-item">
                    <span class="trace-agent">${t.agent_name}</span>
                    <span class="trace-status ${t.status}">${t.status}</span>
                    <span class="trace-duration">${t.duration_ms !== null ? t.duration_ms + 'ms' : '—'}</span>
                </div>`;
            });
        }

        body.innerHTML = html || '<p style="color:var(--text-muted);font-size:0.85rem;">No explainability data.</p>';
    }


    // ═══════════════════════════════════════════════════════════════
    //  SECTION MANAGEMENT
    // ═══════════════════════════════════════════════════════════════

    function showSection(name) {
        Object.values(sections).forEach(s => s.classList.remove('active'));
        if (sections[name]) {
            sections[name].classList.add('active');
        }
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function initNewSessionButton() {
        btnNewSession.addEventListener('click', () => {
            showSection('intake');
            goToStep(1);
            form.reset();
            // Reset modality checkboxes visual state
            document.querySelectorAll('.modality-checkbox').forEach(label => {
                label.classList.remove('checked');
            });
            // Re-check allopathy by default
            const alloCheckbox = document.querySelector('input[value="allopathy"]');
            if (alloCheckbox) {
                alloCheckbox.checked = true;
                alloCheckbox.closest('.modality-checkbox').classList.add('checked');
            }
            btnNewSession.style.display = 'none';
        });
    }


    // ═══════════════════════════════════════════════════════════════
    //  CARD EXPAND / COLLAPSE
    // ═══════════════════════════════════════════════════════════════

    // Expose globally for onclick handlers
    window.toggleCard = function (cardId) {
        const card = document.getElementById(cardId);
        if (card) {
            card.classList.toggle('collapsed');
        }
    };


    // ═══════════════════════════════════════════════════════════════
    //  UTILITY
    // ═══════════════════════════════════════════════════════════════

    function sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }


    // ═══════════════════════════════════════════════════════════════
    //  INITIALIZATION
    // ═══════════════════════════════════════════════════════════════

    function init() {
        initFormNavigation();
        initFormSubmission();
        initNewSessionButton();

        // Health check
        fetch(`${API_BASE}/health`)
            .then(r => r.json())
            .then(data => {
                const statusText = document.querySelector('.status-text');
                if (statusText) statusText.textContent = 'Backend Online';
            })
            .catch(() => {
                const badge = document.getElementById('system-status');
                if (badge) {
                    badge.style.background = 'rgba(255, 71, 87, 0.1)';
                    badge.style.borderColor = 'rgba(255, 71, 87, 0.3)';
                    badge.querySelector('.status-dot').style.background = '#FF4757';
                    badge.querySelector('.status-dot').style.boxShadow = '0 0 8px #FF4757';
                    badge.querySelector('.status-text').textContent = 'Backend Offline';
                    badge.querySelector('.status-text').style.color = '#FF4757';
                }
            });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
