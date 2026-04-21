/**
 * AI Medic — Progressive Web App
 * Mobile-first application logic
 *
 * Features:
 *  - Bottom navigation SPA routing
 *  - Multi-step form with validation
 *  - Pipeline animation with circular progress
 *  - Accordion-based results rendering
 *  - Dark/light theme toggle
 *  - PWA install prompt
 *  - Service worker registration
 *  - Translation system (retained from original)
 */

(function () {
    'use strict';

    // ═══ CONFIG ═══
    const API_BASE = window.location.origin + '/api';

    // ═══ DOM REFS ═══
    const screens = {
        home: document.getElementById('screen-home'),
        analysis: document.getElementById('screen-analysis'),
        results: document.getElementById('screen-results'),
    };
    const navTabs = document.querySelectorAll('.nav-tab');
    const form = document.getElementById('intake-form');
    const btnSubmit = document.getElementById('btn-submit');
    const btnNewSession = document.getElementById('btn-new-session');
    const progressRing = document.getElementById('progress-ring');
    const analysisPercent = document.getElementById('analysis-percent');
    const analysisStatus = document.getElementById('analysis-status');
    const analysisAgent = document.getElementById('analysis-agent');
    const langSelect = document.getElementById('lang-select');
    const themeBtn = document.getElementById('btn-theme');
    const resultsScreen = document.getElementById('screen-results');
    const reportHero = document.getElementById('report-hero');

    // Pipeline config
    const AGENT_ORDER = [
        'normalization', 'triage', 'orchestrator',
        'allopathy_specialist', 'ayurveda_specialist',
        'homeopathy_specialist', 'home_remedial_specialist',
        'safety_conflict', 'recommendation_synthesizer', 'translation_agent',
    ];
    const BACKEND_TO_UI_AGENT = { home_remedial_agent: 'home_remedial_specialist' };

    const LANGUAGE_NAMES = { en: 'English', hi: 'हिन्दी', ta: 'தமிழ்', te: 'తెలుగు', bn: 'বাংলা', mr: 'मराठी' };

    const MODALITY_LABELS = {
        en: { allopathy: 'Allopathy', ayurveda: 'Ayurveda', homeopathy: 'Homeopathy', home_remedial: 'Home Remedies' },
        hi: { allopathy: 'एलोपैथी', ayurveda: 'आयुर्वेद', homeopathy: 'होम्योपैथी', home_remedial: 'घरेलू उपचार' },
        ta: { allopathy: 'அல்லோபதி', ayurveda: 'ஆயுர்வேதம்', homeopathy: 'ஹோமியோபதி', home_remedial: 'வீட்டு நிவாரணம்' },
        te: { allopathy: 'అల్లోపతి', ayurveda: 'ఆయుర్వేదం', homeopathy: 'హోమియోపతి', home_remedial: 'ఇంటి నివారణలు' },
        bn: { allopathy: 'অ্যালোপ্যাথি', ayurveda: 'আয়ুর্বেদ', homeopathy: 'হোমিওপ্যাথি', home_remedial: 'ঘরোয়া উপশম' },
        mr: { allopathy: 'अलोपॅथी', ayurveda: 'आयुर्वेद', homeopathy: 'होमिओपॅथी', home_remedial: 'घरगुती उपाय' },
    };

    const RISK_LABELS = {
        en: { emergent: 'Emergency', urgent: 'Urgent', routine: 'Routine', 'self-care': 'Self-care' },
        hi: { emergent: 'आपातकाल', urgent: 'तत्काल', routine: 'नियमित', 'self-care': 'स्व-देखभाल' },
        ta: { emergent: 'அவசரம்', urgent: 'உடனடி', routine: 'வழக்கமான', 'self-care': 'சுய பராமரிப்பு' },
        te: { emergent: 'అత్యవసరం', urgent: 'తక్షణం', routine: 'సాధారణం', 'self-care': 'స్వీయ సంరక్షణ' },
        bn: { emergent: 'জরুরি', urgent: 'তৎক্ষণাৎ', routine: 'নিয়মিত', 'self-care': 'স্ব-যত্ন' },
        mr: { emergent: 'आपत्कालीन', urgent: 'तातडीचे', routine: 'नियमित', 'self-care': 'स्व-काळजी' },
    };

    const RISK_ACTIONS = {
        emergent: 'Seek immediate medical attention',
        urgent: 'Consult a doctor within 24 hours',
        routine: 'Schedule a regular consultation',
        'self-care': 'Home management recommended',
    };

    let currentLanguage = localStorage.getItem('telehealth-language') || 'en';
    let activeRecommendation = null;
    let currentScreen = 'home';

    // ═══════════════════════════════════════════════════════════════
    //  THEME
    // ═══════════════════════════════════════════════════════════════

    function setThemeColorMeta(theme) {
        document.querySelector('meta[name="theme-color"]').content = theme === 'dark' ? '#0B1220' : '#F5F7FB';
    }

    function setRootTheme(theme, persist = true) {
        document.documentElement.setAttribute('data-theme', theme);
        setThemeColorMeta(theme);
        if (persist) {
            localStorage.setItem('aimedic-theme', theme);
        }
    }

    function initTheme() {
        const stored = localStorage.getItem('aimedic-theme');
        if (stored) {
            setRootTheme(stored, false);
        } else {
            const prefer = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
            setRootTheme(prefer, false);
        }

        themeBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme');
            const next = current === 'dark' ? 'light' : 'dark';
            setRootTheme(next, true);
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  NAVIGATION
    // ═══════════════════════════════════════════════════════════════

    function showScreen(name) {
        currentScreen = name;
        Object.entries(screens).forEach(([key, el]) => {
            el.classList.toggle('active', key === name);
        });
        navTabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.screen === `screen-${name}`);
        });
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    function initNavigation() {
        navTabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const target = tab.dataset.screen.replace('screen-', '');
                showScreen(target);
            });
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  MULTI-STEP FORM
    // ═══════════════════════════════════════════════════════════════

    function getCurrentStep() {
        const active = form.querySelector('.form-step.active');
        return active ? parseInt(active.dataset.step) : 1;
    }

    function goToStep(step) {
        form.querySelectorAll('.form-step').forEach(el => el.classList.remove('active'));
        const target = form.querySelector(`.form-step[data-step="${step}"]`);
        if (target) target.classList.add('active');

        const fill = document.getElementById('step-fill');
        const text = document.getElementById('step-text');
        fill.style.width = `${(step / 4) * 100}%`;
        text.textContent = `Step ${step} of 4`;
    }

    function validateStep(step) {
        if (step === 1) {
            const age = document.getElementById('inp-age').value;
            const sex = document.getElementById('inp-sex').value;
            if (!age || age < 0 || age > 150) { shakeField('inp-age'); return false; }
            if (!sex) { shakeField('inp-sex'); return false; }
        }
        if (step === 2) {
            const symptoms = document.getElementById('inp-symptoms').value.trim();
            if (!symptoms || symptoms.length < 2) { shakeField('inp-symptoms'); return false; }
        }
        return true;
    }

    function shakeField(id) {
        const el = document.getElementById(id);
        el.style.borderColor = 'var(--risk-emergent)';
        el.style.animation = 'shake 0.4s ease';
        el.addEventListener('animationend', () => { el.style.animation = ''; }, { once: true });
        if (!document.getElementById('shake-style')) {
            const s = document.createElement('style');
            s.id = 'shake-style';
            s.textContent = '@keyframes shake{0%,100%{transform:translateX(0)}20%{transform:translateX(-6px)}40%{transform:translateX(6px)}60%{transform:translateX(-4px)}80%{transform:translateX(4px)}}';
            document.head.appendChild(s);
        }
        setTimeout(() => { el.style.borderColor = ''; }, 1500);
    }

    function initFormNav() {
        document.querySelectorAll('.btn-next').forEach(btn => {
            btn.addEventListener('click', () => {
                const current = parseInt(btn.closest('.form-step').dataset.step);
                if (validateStep(current)) goToStep(parseInt(btn.dataset.next));
            });
        });
        document.querySelectorAll('.btn-back').forEach(btn => {
            btn.addEventListener('click', () => {
                goToStep(parseInt(btn.dataset.prev));
            });
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  FORM SUBMISSION
    // ═══════════════════════════════════════════════════════════════

    function buildPayload() {
        const payload = {
            age: parseInt(document.getElementById('inp-age').value),
            sex: document.getElementById('inp-sex').value,
            language_pref: document.getElementById('inp-language').value,
            symptom_text: document.getElementById('inp-symptoms').value.trim(),
        };

        const duration = document.getElementById('inp-duration').value;
        if (duration) payload.duration_days = parseInt(duration);
        const comorbidities = document.getElementById('inp-comorbidities').value.trim();
        if (comorbidities) payload.comorbidities = comorbidities.split(',').map(s => s.trim()).filter(Boolean);
        const meds = document.getElementById('inp-medications').value.trim();
        if (meds) payload.medications = meds.split(',').map(s => s.trim()).filter(Boolean);
        const allergies = document.getElementById('inp-allergies').value.trim();
        if (allergies) payload.allergies = allergies.split(',').map(s => s.trim()).filter(Boolean);
        const lifestyle = document.getElementById('inp-lifestyle').value.trim();
        if (lifestyle) payload.lifestyle_notes = lifestyle;

        return payload;
    }

    function initFormSubmit() {
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!validateStep(4)) return;

            const payload = buildPayload();
            showScreen('analysis');
            resetPipeline();

            btnSubmit.disabled = true;
            btnSubmit.querySelector('.btn-submit-text').style.display = 'none';
            btnSubmit.querySelector('.btn-submit-loader').style.display = 'inline-block';

            try {
                const resp = await fetch(`${API_BASE}/intake`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload),
                });
                if (!resp.ok) {
                    const err = await resp.json();
                    let message = 'API Error';
                    if (typeof err?.detail === 'string') {
                        message = err.detail;
                    } else if (err?.detail?.message) {
                        const reasons = Array.isArray(err.detail.reasons) ? err.detail.reasons : [];
                        message = `${err.detail.message}${reasons.length ? `\n- ${reasons.join('\n- ')}` : ''}`;
                    }
                    throw new Error(message);
                }

                const data = await resp.json();
                await animatePipeline(data.session_id);

                const recResp = await fetch(`${API_BASE}/recommendation/${data.session_id}`);
                if (!recResp.ok) throw new Error('Failed to fetch recommendation');

                const recommendation = await recResp.json();
                renderResults(recommendation);
                showScreen('results');
                btnNewSession.style.display = 'flex';

            } catch (err) {
                console.error('Pipeline error:', err);
                alert(`Error: ${err.message}\n\nMake sure the backend is running.`);
                showScreen('home');
            } finally {
                btnSubmit.disabled = false;
                btnSubmit.querySelector('.btn-submit-text').style.display = '';
                btnSubmit.querySelector('.btn-submit-loader').style.display = 'none';
            }
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  PIPELINE ANIMATION
    // ═══════════════════════════════════════════════════════════════

    const RING_CIRCUMFERENCE = 2 * Math.PI * 54; // 339.292

    function resetPipeline() {
        progressRing.style.strokeDashoffset = RING_CIRCUMFERENCE;
        analysisPercent.textContent = '0%';
        analysisStatus.textContent = 'Starting analysis...';
        analysisAgent.textContent = '';

        document.querySelectorAll('.agent-item').forEach(item => {
            item.classList.remove('running', 'completed');
            item.querySelector('.agent-check').textContent = '○';
        });
    }

    function updatePipelineProgress(completed, total) {
        const pct = Math.round((completed / total) * 100);
        const offset = RING_CIRCUMFERENCE - (RING_CIRCUMFERENCE * pct / 100);
        progressRing.style.strokeDashoffset = offset;
        analysisPercent.textContent = `${pct}%`;
        analysisStatus.textContent = completed >= total ? 'Analysis complete!' : 'Processing...';
    }

    function applyAgentStatus(statusData) {
        const total = statusData?.agents_total || AGENT_ORDER.length;
        const completed = statusData?.agents_completed || 0;
        const currentRaw = statusData?.current_agent || '';
        const current = BACKEND_TO_UI_AGENT[currentRaw] || currentRaw;

        document.querySelectorAll('.agent-item').forEach(item => {
            item.classList.remove('running', 'completed');
            item.querySelector('.agent-check').textContent = '○';
        });

        AGENT_ORDER.forEach((name, idx) => {
            const item = document.querySelector(`.agent-item[data-agent="${name}"]`);
            if (!item) return;
            if (idx < completed) {
                item.classList.add('completed');
                item.querySelector('.agent-check').textContent = '✓';
            }
        });

        if (current) {
            const running = document.querySelector(`.agent-item[data-agent="${current}"]`);
            if (running && !running.classList.contains('completed')) {
                running.classList.add('running');
                running.querySelector('.agent-check').textContent = '⟳';
                analysisAgent.textContent = `Running: ${running.querySelector('.agent-name').textContent}`;
            }
        }

        updatePipelineProgress(completed, total);
    }

    async function animatePipeline(sessionId) {
        let pollingWorked = false;

        for (let i = 0; i < 240; i++) {
            try {
                const resp = await fetch(`${API_BASE}/status/${sessionId}`);
                if (!resp.ok) break;
                pollingWorked = true;
                const data = await resp.json();
                applyAgentStatus(data);

                if (data.status === 'completed' || data.status === 'error') return;
                await sleep(450);
            } catch (_) { break; }
        }

        if (!pollingWorked) {
            // Fallback: simulate pipeline visually
            for (let i = 0; i < AGENT_ORDER.length; i++) {
                const item = document.querySelector(`.agent-item[data-agent="${AGENT_ORDER[i]}"]`);
                if (item) {
                    item.classList.add('running');
                    item.querySelector('.agent-check').textContent = '⟳';
                    analysisAgent.textContent = `Running: ${item.querySelector('.agent-name').textContent}`;
                }
                await sleep(300 + Math.random() * 250);
                if (item) {
                    item.classList.remove('running');
                    item.classList.add('completed');
                    item.querySelector('.agent-check').textContent = '✓';
                }
                updatePipelineProgress(i + 1, AGENT_ORDER.length);
            }
            await sleep(500);
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  RESULTS RENDERING
    // ═══════════════════════════════════════════════════════════════

    function renderResults(rec) {
        activeRecommendation = rec;
        const lang = currentLanguage;
        const labels = RISK_LABELS[lang] || RISK_LABELS.en;
        const modLabels = MODALITY_LABELS[lang] || MODALITY_LABELS.en;

        // Risk Card
        const riskLevel = rec.risk_level || 'routine';
        const riskCard = document.getElementById('risk-card');
        riskCard.className = `risk-card ${riskLevel}`;
        document.getElementById('risk-badge').textContent = labels[riskLevel] || riskLevel.toUpperCase();
        document.getElementById('risk-score').textContent = `Score: ${Math.round(rec.risk_score || 0)}/100`;
        document.getElementById('risk-conf').textContent = `Confidence: ${Math.round((rec.risk_confidence || 0) * 100)}%`;

        const justText = rec.triage_justification || '—';
        document.getElementById('risk-just').textContent = justText.length > 200 ? justText.substring(0, 200) + '...' : justText;
        document.getElementById('risk-action').textContent = RISK_ACTIONS[riskLevel] || '';

        renderReportHero(rec, labels);

        // Doctor
        renderDoctor(rec);

        // Care Path
        renderCarePath(rec.care_path || [], modLabels);

        // Plans
        renderPlans(rec.plan_segments || [], modLabels, rec.doctor_recommendation || null);

        // Warnings
        renderWarnings(rec.warnings || []);

        // Evidence
        renderEvidence(rec.provenance || []);

        // Update badges
        document.getElementById('carepath-count').textContent = (rec.care_path || []).length;
        document.getElementById('plans-count').textContent = (rec.plan_segments || []).length;
        document.getElementById('warnings-count').textContent = (rec.warnings || []).length;
        document.getElementById('evidence-count').textContent = (rec.provenance || []).length;

        animateReportEntrance();
    }

    function renderReportHero(rec, labels) {
        if (!reportHero) return;

        const doctor = rec.doctor_recommendation?.doctor_name || 'Specialist pending';
        const bestModality = rec.doctor_recommendation?.best_modality || 'general';
        const riskText = labels[rec.risk_level || 'routine'] || 'Routine';
        const riskScore = Math.round(rec.risk_score || 0);
        const confidence = Math.round((rec.risk_confidence || 0) * 100);
        const stepCount = (rec.care_path || []).length;
        const warningCount = (rec.warnings || []).length;

        reportHero.innerHTML = `
            <div class="report-hero-kicker">Clinical Decision Summary</div>
            <h3 class="report-hero-title">AI-guided care strategy personalized for this patient profile</h3>
            <div class="report-hero-meta">Lead specialist: ${esc(doctor)} · Best track: ${esc(bestModality.replace(/_/g, ' '))}</div>
            <div class="report-hero-chip-grid">
                <div class="report-hero-chip"><span class="chip-label">Risk Band</span><span class="chip-value">${esc(riskText)}</span></div>
                <div class="report-hero-chip"><span class="chip-label">Risk Score</span><span class="chip-value">${riskScore}/100</span></div>
                <div class="report-hero-chip"><span class="chip-label">Confidence</span><span class="chip-value">${confidence}%</span></div>
                <div class="report-hero-chip"><span class="chip-label">Care Steps</span><span class="chip-value">${stepCount}</span></div>
                <div class="report-hero-chip"><span class="chip-label">Warnings</span><span class="chip-value">${warningCount}</span></div>
            </div>
        `;
    }

    function animateReportEntrance(isThemeSwitch = false) {
        if (!resultsScreen) return;
        const targets = resultsScreen.querySelectorAll('#report-hero, .risk-card, .result-section, .disclaimer-bar, .btn-new-session');
        if (!targets.length) return;

        if (window.gsap) {
            window.gsap.killTweensOf(targets);
            window.gsap.fromTo(
                targets,
                {
                    y: isThemeSwitch ? 8 : 22,
                    opacity: isThemeSwitch ? 0.85 : 0,
                    filter: isThemeSwitch ? 'blur(0.6px)' : 'blur(3px)'
                },
                {
                    y: 0,
                    opacity: 1,
                    filter: 'blur(0px)',
                    duration: isThemeSwitch ? 0.32 : 0.55,
                    stagger: isThemeSwitch ? 0.02 : 0.05,
                    ease: 'power2.out'
                }
            );
        }
    }

    function renderDoctor(rec) {
        const body = document.getElementById('doctor-content');
        const doc = rec.doctor_recommendation;
        if (!doc) {
            body.innerHTML = '<div class="empty-state">No doctor assignment available for this session.</div>';
            return;
        }

        const getModalityIcon = (modality) => {
            const icons = {
                allopathy: '🏥',
                ayurveda: '🌿',
                homeopathy: '💧',
                home_remedial: '🏠'
            };
            return icons[modality] || '⚕️';
        };

        const formatModality = (modality) => (modality || 'General').replace(/_/g, ' ');

        const getInitials = (name) => {
            const parts = String(name || 'Doctor').trim().split(/\s+/).filter(Boolean);
            if (!parts.length) return 'DR';
            if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        };

        const bestMod = (doc.modality_recommendations || []).find(m => m.modality === doc.best_modality);
        const bestScore = bestMod ? Math.round((bestMod.suitability_score || 0) * 100) : 0;
        const bestIcon = getModalityIcon(doc.best_modality);
        const doctorInitials = getInitials(doc.doctor_name);

        const alternatives = (doc.modality_recommendations || [])
            .filter(m => m.modality !== doc.best_modality)
            .sort((a, b) => (b.suitability_score || 0) - (a.suitability_score || 0))
            .slice(0, 3);

        const altRows = alternatives.map((item, idx) => {
            const pct = Math.round((item.suitability_score || 0) * 100);
            return `
                <div class="doctor-clean-alt-row">
                    <div class="doctor-clean-alt-main">
                        <span class="doctor-clean-alt-index">${idx + 1}</span>
                        <div>
                            <p class="doctor-clean-alt-modality">${esc(formatModality(item.modality))}</p>
                            <p class="doctor-clean-alt-type">${esc(item.doctor_type)}</p>
                        </div>
                    </div>
                    <span class="doctor-clean-alt-score">${pct}%</span>
                </div>
            `;
        }).join('');

        body.innerHTML = `
            <section class="doctor-clean-shell">
                <header class="doctor-clean-head">
                    <div class="doctor-clean-avatar">${esc(doctorInitials)}</div>
                    <div class="doctor-clean-identity">
                        <p class="doctor-clean-kicker">Assigned Specialist</p>
                        <h4 class="doctor-clean-name">${esc(doc.doctor_name)}</h4>
                        <p class="doctor-clean-specialty">${esc(doc.specialty)}</p>
                    </div>
                    <span class="doctor-clean-modality">${bestIcon} ${esc(formatModality(doc.best_modality))}</span>
                </header>

                <div class="doctor-clean-meta-grid">
                    <div class="doctor-clean-meta-item">
                        <span class="doctor-clean-meta-label">Consultation</span>
                        <span class="doctor-clean-meta-value">${esc(doc.consultation_mode)}</span>
                    </div>
                    <div class="doctor-clean-meta-item">
                        <span class="doctor-clean-meta-label">Next Available</span>
                        <span class="doctor-clean-meta-value">${esc(doc.next_available_window)}</span>
                    </div>
                    ${doc.urgency_note ? `
                    <div class="doctor-clean-meta-item doctor-clean-meta-full">
                        <span class="doctor-clean-meta-label">Urgency</span>
                        <span class="doctor-clean-meta-value">${esc(doc.urgency_note)}</span>
                    </div>` : ''}
                </div>

                <div class="doctor-clean-score">
                    <div class="doctor-clean-score-head">
                        <span>Clinical Match</span>
                        <strong>${bestScore}%</strong>
                    </div>
                    <div class="doctor-clean-score-track"><span style="width:${bestScore}%"></span></div>
                </div>

                ${alternatives.length ? `
                    <div class="doctor-clean-alt">
                        <p class="doctor-clean-alt-title">Alternative Specialists</p>
                        ${altRows}
                    </div>
                ` : ''}
            </section>
        `;
    }

    function renderCarePath(steps, modLabels) {
        const body = document.getElementById('carepath-content');
        if (!steps.length) { body.innerHTML = '<div class="empty-state">No care path generated.</div>'; return; }
        body.innerHTML = steps.map(step => {
            const icon = step.modality === 'allopathy' ? '🏥' : step.modality === 'ayurveda' ? '🌿' : step.modality === 'homeopathy' ? '💧' : '🏠';
            const modLabel = modLabels[step.modality] || step.modality;
            return `
                <div class="care-step fade-in-up">
                    <div class="care-step-head">
                        <span class="care-step-num">Step ${step.step_number}</span>
                        <span class="care-priority ${step.priority}">${step.priority}</span>
                    </div>
                    <div class="care-modality">${icon} ${esc(modLabel)}</div>
                    <div class="care-specialist">${esc(step.specialist_type)}</div>
                    <div class="care-reason">${esc(step.reason)}</div>
                </div>
            `;
        }).join('');
    }

    function renderPlans(segments, modLabels, doctorRecommendation) {
        const body = document.getElementById('plans-content');
        const primarySegments = Array.isArray(segments) ? segments : [];
        const allModalityOptions = doctorRecommendation?.modality_recommendations || [];
        const bestModality = doctorRecommendation?.best_modality || null;
        const alternativeOptions = allModalityOptions
            .filter(item => item.modality !== bestModality)
            .sort((a, b) => (b.suitability_score || 0) - (a.suitability_score || 0))
            .slice(0, 3);

        if (!primarySegments.length && !alternativeOptions.length) {
            body.innerHTML = '<div class="empty-state">No treatment plans generated.</div>';
            return;
        }

        const primaryHtml = primarySegments.map(seg => {
            const icon = seg.modality === 'allopathy' ? '🏥' : seg.modality === 'ayurveda' ? '🌿' : seg.modality === 'homeopathy' ? '💧' : '🏠';
            const modLabel = modLabels[seg.modality] || seg.modality;
            const coreSteps = (seg.recommendations || []).slice(0, 3);
            const dailyHabits = (seg.lifestyle || []).slice(0, 3);
            const confidence = Math.round((seg.confidence || 0) * 100);

            const chips = [...coreSteps, ...dailyHabits].slice(0, 6).map(item => {
                const compact = item.length > 60 ? `${item.substring(0, 57)}...` : item;
                return `<span class="plan-chip">${esc(compact)}</span>`;
            }).join('');

            const summaryText = seg.title || 'Guided care pathway';
            const followup = seg.follow_up ? `<div class="plan-modern-followup">Next check-in: ${esc(seg.follow_up)}</div>` : '';

            return `
                <article class="plan-modern-card fade-in-up">
                    <header class="plan-modern-head">
                        <div class="plan-modern-title-wrap">
                            <h4 class="plan-modern-title">${icon} ${esc(modLabel)}</h4>
                            <p class="plan-modern-summary">${esc(summaryText)}</p>
                        </div>
                        <div class="plan-modern-score">${confidence}% match</div>
                    </header>

                    <div class="plan-modern-grid">
                        <div class="plan-modern-block">
                            <div class="plan-modern-label">Top Actions</div>
                            <p class="plan-modern-main">${esc(coreSteps[0] || 'Follow rest, hydration, and symptom monitoring guidance.')}</p>
                        </div>
                        <div class="plan-modern-block accent">
                            <div class="plan-modern-label">Daily Focus</div>
                            <p class="plan-modern-main">${esc(dailyHabits[0] || 'Keep a simple routine with sleep, nutrition, and stress control.')}</p>
                        </div>
                    </div>

                    <div class="plan-modern-chips">${chips || '<span class="plan-chip">Personalized non-medication guidance</span>'}</div>
                    ${followup}
                </article>
            `;
        }).join('');

        const alternativesHtml = alternativeOptions.map(option => {
            const icon = option.modality === 'allopathy' ? '🏥' : option.modality === 'ayurveda' ? '🌿' : option.modality === 'homeopathy' ? '💧' : '🏠';
            const modLabel = modLabels[option.modality] || option.modality;
            const pct = Math.round((option.suitability_score || 0) * 100);
            const descriptor = option.recommended ? 'High-fit alternative' : 'Alternative option';

            return `
                <article class="alt-plan-card fade-in-up">
                    <div class="alt-plan-head">
                        <h5 class="alt-plan-title">${icon} ${esc(modLabel)}</h5>
                        <span class="alt-plan-score">${pct}%</span>
                    </div>
                    <p class="alt-plan-doctor">${esc(option.doctor_type)}</p>
                    <p class="alt-plan-rationale">${esc(option.rationale || descriptor)}</p>
                    <span class="alt-plan-tag">${descriptor}</span>
                </article>
            `;
        }).join('');

        body.innerHTML = `
            <div class="plan-board">
                ${primarySegments.length ? `
                    <div class="plan-stack-title">Primary Treatment Path</div>
                    <div class="plan-primary-grid">${primaryHtml}</div>
                ` : ''}
                ${alternativeOptions.length ? `
                    <div class="plan-stack-title alt">Alternative Paths Suggested By AI</div>
                    <div class="plan-alternatives-grid">${alternativesHtml}</div>
                ` : ''}
            </div>
        `;
    }

    function renderWarnings(warnings) {
        const body = document.getElementById('warnings-content');
        if (!warnings.length) {
            body.innerHTML = '<div class="empty-state">✅ No safety warnings — care plan is clear.</div>';
            return;
        }
        body.innerHTML = warnings.map(w => `
            <div class="warning-item ${w.severity || 'low'} fade-in-up">
                <span class="warning-sev">${(w.severity || 'low').toUpperCase()}</span>
                <p class="warning-msg">${esc(w.message)}</p>
                ${w.resolution ? `<p class="warning-resolution">💡 ${esc(w.resolution)}</p>` : ''}
            </div>
        `).join('');
    }

    function renderEvidence(evidence) {
        const body = document.getElementById('evidence-content');
        if (!evidence.length) {
            body.innerHTML = '<div class="empty-state">No evidence sources cited.</div>';
            return;
        }
        body.innerHTML = evidence.map(ev => `
            <div class="evidence-item fade-in-up">
                <span class="evidence-tier">Tier ${ev.reliability_tier || '?'}</span>
                <div class="evidence-item-title">${esc(ev.title)}</div>
                <div class="evidence-item-meta">${esc(ev.source_type || '')}${ev.year ? ` (${ev.year})` : ''}</div>
            </div>
        `).join('');
    }

    // ═══════════════════════════════════════════════════════════════
    //  ACCORDION TOGGLES
    // ═══════════════════════════════════════════════════════════════

    function initAccordions() {
        document.querySelectorAll('.section-toggle').forEach(btn => {
            btn.addEventListener('click', () => {
                const targetId = btn.dataset.target;
                const content = document.getElementById(targetId);
                const isOpen = content.classList.contains('open');

                content.classList.toggle('open', !isOpen);
                btn.setAttribute('aria-expanded', !isOpen);
            });
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  NEW SESSION
    // ═══════════════════════════════════════════════════════════════

    function initNewSession() {
        btnNewSession.addEventListener('click', () => {
            showScreen('home');
            goToStep(1);
            form.reset();
            btnNewSession.style.display = 'none';
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  TRANSLATION API
    // ═══════════════════════════════════════════════════════════════

    async function translateTexts(texts, langCode) {
        if (!texts.length || langCode === 'en') return texts.slice();
        try {
            const resp = await fetch(`${API_BASE}/translate/text`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ language_code: langCode, texts }),
            });
            if (!resp.ok) return texts.slice();
            const data = await resp.json();
            return Array.isArray(data.translated_texts) ? data.translated_texts : texts.slice();
        } catch (_) {
            return texts.slice();
        }
    }

    // ═══════════════════════════════════════════════════════════════
    //  LANGUAGE
    // ═══════════════════════════════════════════════════════════════

    function initLanguage() {
        langSelect.value = currentLanguage;
        langSelect.addEventListener('change', async (e) => {
            currentLanguage = e.target.value;
            localStorage.setItem('telehealth-language', currentLanguage);
            document.documentElement.lang = currentLanguage;
            // Re-render results if available
            if (activeRecommendation) renderResults(activeRecommendation);
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  PWA: SERVICE WORKER + INSTALL PROMPT
    // ═══════════════════════════════════════════════════════════════

    let deferredPrompt = null;

    function initPWA() {
        // Register service worker
        if ('serviceWorker' in navigator) {
            navigator.serviceWorker.register('/static/sw.js')
                .then(reg => console.log('SW registered:', reg.scope))
                .catch(err => console.log('SW registration failed:', err));
        }

        // Install prompt
        window.addEventListener('beforeinstallprompt', (e) => {
            e.preventDefault();
            deferredPrompt = e;
            const banner = document.getElementById('pwa-install-banner');
            banner.style.display = '';
        });

        document.getElementById('pwa-install-btn').addEventListener('click', async () => {
            if (!deferredPrompt) return;
            deferredPrompt.prompt();
            const result = await deferredPrompt.userChoice;
            console.log('Install result:', result.outcome);
            deferredPrompt = null;
            document.getElementById('pwa-install-banner').style.display = 'none';
        });

        document.getElementById('pwa-dismiss-btn').addEventListener('click', () => {
            document.getElementById('pwa-install-banner').style.display = 'none';
        });
    }

    // ═══════════════════════════════════════════════════════════════
    //  HEALTH CHECK
    // ═══════════════════════════════════════════════════════════════

    function initHealthCheck() {
        fetch(`${API_BASE}/health`)
            .then(r => r.json())
            .then(() => {
                document.getElementById('stat-status').textContent = 'Online';
            })
            .catch(() => {
                document.getElementById('stat-status').textContent = 'Offline';
                const dot = document.querySelector('.status-dot-live');
                if (dot) dot.classList.add('offline');
            });
    }

    // ═══════════════════════════════════════════════════════════════
    //  UTILITIES
    // ═══════════════════════════════════════════════════════════════

    function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

    function esc(text) {
        const d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    }

    // ═══════════════════════════════════════════════════════════════
    //  INIT
    // ═══════════════════════════════════════════════════════════════

    function init() {
        initTheme();
        initNavigation();
        initFormNav();
        initFormSubmit();
        initAccordions();
        initNewSession();
        initLanguage();
        initPWA();
        initHealthCheck();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
