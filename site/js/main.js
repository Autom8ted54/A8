// Kansenradar — Wachtlijst formulier afhandeling

// Formspree form ID — vervang door jouw ID van formspree.io
const FORMSPREE_ID = 'JOUW_FORM_ID';

(function () {
    'use strict';

    const form = document.getElementById('waitlist-form');
    const successMsg = document.getElementById('waitlist-success');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn?.querySelector('.btn-text');
    const btnLoading = submitBtn?.querySelector('.btn-loading');

    if (!form) return;

    // ---- Validatie helpers ----

    function showError(fieldId, message) {
        const el = document.getElementById(fieldId + '-error');
        if (el) el.textContent = message;
        const input = document.getElementById(fieldId) || document.querySelector('[name="' + fieldId + '"]');
        if (input) input.classList.add('error');
    }

    function clearError(fieldId) {
        const el = document.getElementById(fieldId + '-error');
        if (el) el.textContent = '';
        const input = document.getElementById(fieldId) || document.querySelector('[name="' + fieldId + '"]');
        if (input) input.classList.remove('error');
    }

    function clearAllErrors() {
        ['email', 'schrijft', 'uren', 'tool', 'medewerkers'].forEach(clearError);
    }

    function getRadioValue(name) {
        const checked = form.querySelector('[name="' + name + '"]:checked');
        return checked ? checked.value : null;
    }

    function isValidEmail(email) {
        return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
    }

    function validateForm(data) {
        let valid = true;
        clearAllErrors();

        if (!data.email || !isValidEmail(data.email)) {
            showError('email', 'Vul een geldig e-mailadres in.');
            valid = false;
        }

        if (!data.schrijft_al_in) {
            showError('schrijft', 'Maak een keuze.');
            valid = false;
        }

        if (!data.uren_per_week) {
            showError('uren', 'Maak een keuze.');
            valid = false;
        }

        if (!data.gebruikt_tool) {
            showError('tool', 'Maak een keuze.');
            valid = false;
        }

        if (!data.aantal_medewerkers) {
            showError('medewerkers', 'Maak een keuze.');
            valid = false;
        }

        return valid;
    }

    // ---- Loading state ----

    function setLoading(loading) {
        submitBtn.disabled = loading;
        if (btnText) btnText.hidden = loading;
        if (btnLoading) btnLoading.hidden = !loading;
    }

    // ---- Form submit ----

    form.addEventListener('submit', async function (e) {
        e.preventDefault();

        const data = {
            email: (document.getElementById('email')?.value || '').trim().toLowerCase(),
            schrijft_al_in: getRadioValue('schrijft_al_in'),
            uren_per_week: getRadioValue('uren_per_week'),
            gebruikt_tool: getRadioValue('gebruikt_tool'),
            grootste_frustratie: (document.getElementById('frustratie')?.value || '').trim(),
            aantal_medewerkers: getRadioValue('aantal_medewerkers'),
        };

        if (!validateForm(data)) {
            // Scroll to first error
            const firstError = form.querySelector('.field-error:not(:empty)');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
            return;
        }

        setLoading(true);

        try {
            const response = await fetch(`https://formspree.io/f/${FORMSPREE_ID}`, {
                method: 'POST',
                headers: { 'Accept': 'application/json' },
                body: new URLSearchParams(data),
            });

            if (response.ok) {
                form.hidden = true;
                successMsg.hidden = false;
                successMsg.scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                const result = await response.json().catch(() => ({}));
                if (result.errors) {
                    showError('email', result.errors.map(e => e.message).join('. '));
                } else {
                    showError('email', 'Er is iets misgegaan. Probeer het opnieuw of mail naar hello@autom8ted.be.');
                }
                setLoading(false);
            }
        } catch (err) {
            showError('email', 'Verbindingsfout. Controleer je internet en probeer opnieuw.');
            setLoading(false);
        }
    });

    // ---- Live email validatie op blur ----
    const emailInput = document.getElementById('email');
    if (emailInput) {
        emailInput.addEventListener('blur', function () {
            if (this.value && !isValidEmail(this.value.trim())) {
                showError('email', 'Vul een geldig e-mailadres in.');
            } else {
                clearError('email');
            }
        });
    }

})();
