/**
 * "Send to Developer" interaction packet export modal & handlers.
 */

const FEEDBACK_CATEGORIES = [
    'Bug report',
    'Dysfluent speech',
    '/t/ /d/ ends',
    '/r/ ends',
    'Timing',
    'Bad animation',
    'Missed / false cue',
    'Other',
];

function collectTabContext(tabName) {
    if (tabName === 'analysis') {
        const targetText = document.getElementById('target_text')?.value || '';
        const res = window.recorder?.lastAnalysisResult || null;
        const compactPayload = res
            ? {
                status: res.status,
                integration_meta: res.integration_meta,
                alignment_meta: res.alignment_meta,
                prosody: res.prosody,
                alignment: res.alignment,
                pronunciation_diagnostics: res.pronunciation_diagnostics,
                errors: res.errors,
            }
            : {};
        return {
            tab: 'analysis',
            targetText,
            audioBlob: window.recorder?.lastAudioBlob || null,
            audioFilename: 'analysis_recording.wav',
            payload: compactPayload,
        };
    }

    if (tabName === 'prosody') {
        const prosody = window.prosodyLabRecorder;
        const customText = document.getElementById('prosody-custom-text')?.value || '';
        const phraseSelect = document.getElementById('prosody-phrase-select');
        const phraseLabel = phraseSelect?.selectedOptions?.[0]?.textContent || customText;
        const history = prosody?.loadHistory?.() || [];
        return {
            tab: 'prosody',
            targetText: prosody?.phraseId === 'custom' ? customText : phraseLabel,
            audioBlob: prosody?.latestRecordedBlob || null,
            audioFilename: 'prosody_recording.wav',
            payload: {
                phrase_id: prosody?.phraseId,
                audio_mode: prosody?.audioMode,
                latest_record: history[0] || null,
            },
        };
    }

    const lab = window.comparisonLab;
    return {
        tab: 'comparison',
        targetText: document.getElementById('comparison-target-text')?.value || lab?.currentTargetText || '',
        audioBlob: lab?.lastStudentAudioBlob || null,
        audioFilename: 'comparison_student.wav',
        payload: {
            reference_loaded: Boolean(lab?.referenceLoaded),
            student_loaded: Boolean(lab?.studentLoaded),
        },
    };
}

export function initFeedbackExport() {
    const modal = document.getElementById('dev-feedback-modal');
    const form = document.getElementById('dev-feedback-form');
    const cancelBtn = document.getElementById('dev-feedback-cancel');
    const categoriesBox = document.getElementById('dev-feedback-categories');
    const noteInput = document.getElementById('dev-feedback-note');
    const statusEl = document.getElementById('dev-feedback-status');
    const tabLabel = document.getElementById('dev-feedback-tab-label');
    const audioBadge = document.getElementById('dev-feedback-audio-badge');
    const submitBtn = document.getElementById('dev-feedback-submit');
    if (!modal || !form || !categoriesBox) return;

    let activeTab = 'analysis';

    if (categoriesBox.children.length === 0) {
        FEEDBACK_CATEGORIES.forEach((label) => {
            const pill = document.createElement('label');
            pill.className = 'inline-flex items-center gap-1.5 rounded-full border border-gray-300 bg-gray-50 px-3 py-1 text-xs text-gray-700 cursor-pointer hover:bg-blue-50';
            const input = document.createElement('input');
            input.type = 'checkbox';
            input.value = label;
            input.className = 'rounded text-blue-600';
            const span = document.createElement('span');
            span.textContent = label;
            pill.append(input, span);
            categoriesBox.appendChild(pill);
        });
    }

    const openModal = (tabName) => {
        activeTab = tabName || window.currentTab || 'analysis';
        const ctx = collectTabContext(activeTab);
        if (tabLabel) tabLabel.textContent = activeTab;
        if (audioBadge) {
            audioBadge.textContent = ctx.audioBlob ? 'Includes recorded audio' : 'No audio recorded yet (metadata/text only)';
            audioBadge.className = ctx.audioBlob
                ? 'inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-medium text-emerald-800'
                : 'inline-flex items-center rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-600';
        }
        if (statusEl) statusEl.textContent = '';
        if (noteInput) noteInput.value = '';
        categoriesBox.querySelectorAll('input[type="checkbox"]').forEach((cb) => {
            cb.checked = false;
        });
        modal.classList.remove('hidden');
        noteInput?.focus();
    };

    const closeModal = () => {
        modal.classList.add('hidden');
    };

    document.querySelectorAll('[data-dev-export-tab]').forEach((btn) => {
        btn.addEventListener('click', () => openModal(btn.getAttribute('data-dev-export-tab')));
    });

    cancelBtn?.addEventListener('click', closeModal);
    modal.addEventListener('click', (event) => {
        if (event.target === modal) closeModal();
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        if (submitBtn) submitBtn.disabled = true;
        if (statusEl) statusEl.textContent = 'Saving packet…';

        const ctx = collectTabContext(activeTab);
        const selectedCats = Array.from(categoriesBox.querySelectorAll('input[type="checkbox"]:checked'))
            .map((cb) => cb.value);
        const formData = new FormData();
        formData.append('tab', ctx.tab);
        formData.append('categories', JSON.stringify(selectedCats));
        formData.append('note', noteInput?.value || '');
        formData.append('target_text', ctx.targetText);
        formData.append('payload_json', JSON.stringify(ctx.payload));
        if (ctx.audioBlob) {
            formData.append('audio', ctx.audioBlob, ctx.audioFilename);
        }

        try {
            const resp = await fetch('/api/export-feedback', {
                method: 'POST',
                body: formData,
            });
            if (!resp.ok) {
                const err = await resp.json().catch(() => null);
                throw new Error(err?.detail || `HTTP ${resp.status}`);
            }
            const data = await resp.json();
            if (statusEl) {
                statusEl.textContent = `Saved to Builds folder (${data.folder_name}).`;
            }
            setTimeout(closeModal, 900);
        } catch (err) {
            if (statusEl) {
                statusEl.textContent = `Export failed: ${err.message}`;
            }
        } finally {
            if (submitBtn) submitBtn.disabled = false;
        }
    });
}
