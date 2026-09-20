const $ = id => document.getElementById(id);

let experts = [];
let expertId = null;
let selectedExpert = null;

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value ?? "";
  return node.innerHTML;
}

function initials(name) {
  return (name || "AI").split(/\s+/).filter(Boolean).slice(0, 2)
    .map(part => part[0].toUpperCase()).join("");
}

function avatarHue(name) {
  return [...(name || "")].reduce((sum, character) => sum + character.charCodeAt(0), 0) % 360;
}

async function api(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = response.statusText;
    try { detail = (await response.json()).detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function notice(text, error = false) {
  $("notice").className = `notice${error ? " error" : ""}`;
  $("notice").textContent = text;
}

async function withBusy(form, label, action) {
  const button = form.querySelector('button[type="submit"]');
  const original = button.textContent;
  button.disabled = true;
  button.textContent = label;
  form.setAttribute("aria-busy", "true");
  try {
    return await action();
  } finally {
    button.disabled = false;
    button.textContent = original;
    form.removeAttribute("aria-busy");
  }
}

function selectedName() {
  return selectedExpert?.name || "Selected expert";
}

function updateIdentity() {
  selectedExpert = experts.find(expert => expert.id === expertId) || null;
  const name = selectedName();
  $("twinName").textContent = `${name} (AI Clone)`;
  $("twinAvatar").textContent = initials(name);
  $("twinAvatar").style.setProperty("--avatar-hue", avatarHue(name));
  $("question").placeholder = `Ask ${name}'s AI Twin…`;
  $("selectedExpertDisclaimer").textContent = `${name} (AI Clone)`;
  document.querySelectorAll(".person").forEach(person => {
    person.classList.toggle("selected", person.dataset.person === name.toLowerCase());
  });
}

function resetConversation() {
  $("messages").innerHTML = `
    <div class="message-row system">
      <div class="message">Ask ${escapeHtml(selectedName())}'s AI Twin about a decision, tradeoff, incident, or measured outcome.</div>
    </div>`;
  $("evidenceStrength").className = "evidence-strength";
  $("evidenceStrength").textContent = "Evidence: waiting";
}

async function loadPortfolioSummary() {
  const summary = await api("/api/portfolio-summary");
  $("projectMetric").textContent = summary.projects.length;
  $("sourceMetric").textContent = summary.source_count;
  $("decisionMetric").textContent = summary.decision_count;
  $("cloneMetric").textContent = summary.expert_count;
}

function citationMarkup(citations) {
  if (!citations.length) return "";
  return `
    <details class="answer-evidence">
      <summary>${citations.length} source citation${citations.length === 1 ? "" : "s"}</summary>
      <div class="citation-list">${citations.map((citation, index) => {
        const attributed = citation.attribution_status === "expert_attributed";
        const role = citation.evidence_role ? ` (${citation.evidence_role})` : "";
        const thread = citation.parent_comment_id
          ? ` · reply to ${citation.parent_author || "reviewer"} comment ${citation.parent_comment_id}`
          : "";
        const provenance = attributed
          ? `Expert-attributed · ${citation.evidence_author || "selected expert"}${role}${thread}`
          : citation.evidence_author
            ? `Attributed context · ${citation.evidence_author}${role}${thread}`
            : "Unattributed context";
        const confidence = citation.decision_confidence == null
          ? "confidence unavailable"
          : `${Math.round(citation.decision_confidence * 100)}% extraction confidence`;
        return `
          <article class="citation ${attributed ? "expert" : "context"}">
            <strong>[${index + 1}] ${escapeHtml(citation.source_title)}</strong>
            <small>${escapeHtml(citation.page_or_segment)}</small>
            <small>${escapeHtml(provenance)} · ${escapeHtml(confidence)}</small>
            <details><summary>Show excerpt</summary><p>${escapeHtml(citation.excerpt)}</p></details>
          </article>`;
      }).join("")}</div>
    </details>`;
}

function renderExpertMatches(response) {
  if (!response.matches.length) {
    $("expertFinderResult").innerHTML = `
      <div class="empty-state">No attributable evidence matched this question. Try naming a technology, architecture decision, incident, or delivery concern.</div>`;
    return;
  }
  $("expertFinderResult").innerHTML = `
    <div class="expert-match-summary">
      <strong>${response.matches.length} evidence-backed matches</strong>
      <span>${escapeHtml(response.simulation_notice)}</span>
    </div>
    <div class="expert-match-list">${response.matches.map((match, index) => `
      <article class="expert-match">
        <div class="expert-match-rank">${String(index + 1).padStart(2, "0")}</div>
        <span class="avatar" style="--avatar-hue:${avatarHue(match.expert_name)}"
              aria-hidden="true">${escapeHtml(initials(match.expert_name))}</span>
        <div class="expert-match-body">
          <div class="expert-match-heading">
            <div><h3>${escapeHtml(match.expert_name)} <small>(AI Clone)</small></h3>
              <p>${escapeHtml(match.role)}</p></div>
            <span class="match-score ${escapeHtml(match.confidence)}">${Math.round(match.score * 100)}% match</span>
          </div>
          <p>${escapeHtml(match.explanation)}</p>
          <div class="matched-terms">${match.matched_terms.map(term =>
            `<span>${escapeHtml(term)}</span>`).join("")}</div>
          <div class="expert-match-meta">${match.evidence_count} cited decisions ·
            ${match.project_count} synthetic project${match.project_count === 1 ? "" : "s"}</div>
          ${citationMarkup(match.citations)}
          <button type="button" class="ask-matched-expert"
                  data-expert-name="${escapeHtml(match.expert_name)}">Ask this AI Clone →</button>
        </div>
      </article>`).join("")}</div>`;
}

function citationRefs(citationIds) {
  if (!citationIds?.length) return '<span class="muted">No supporting citation</span>';
  return `<span class="muted">Evidence: ${citationIds.map(id =>
    `<code>${escapeHtml(id.slice(0, 8))}</code>`).join(", ")}</span>`;
}

function renderWarRoom(response) {
  const decision = response.final_decision;
  const citationIds = new Set(decision.citation_ids || []);
  const verifiedCitations = (response.citations || []).filter(citation =>
    citationIds.has(citation.decision_id));
  $("warRoomResult").innerHTML = `
    <section class="war-room-panel" aria-labelledby="warRoomConversationTitle">
      <h3 id="warRoomConversationTitle">Group conversation</h3>
      <div class="war-room-conversation">
        <article class="war-room-message user-opening">
          <span class="avatar" aria-hidden="true">YO</span>
          <div>
            <strong>You</strong>
            <small>Opening topic</small>
            <p>${escapeHtml(response.topic)}</p>
          </div>
        </article>
        ${response.messages.map(message => `
          <article class="war-room-message ${escapeHtml(message.message_type)}">
            <span class="avatar" style="--avatar-hue:${avatarHue(message.speaker)}"
                  aria-hidden="true">${escapeHtml(initials(message.speaker))}</span>
            <div>
              <strong>${escapeHtml(message.speaker)} (AI Clone)</strong>
              <small>${escapeHtml(message.role)} · ${escapeHtml(message.message_type)} ·
                ${escapeHtml(message.evidence_strength)} evidence</small>
              ${message.responds_to
                ? `<span class="reply-marker">Replying to ${escapeHtml(message.responds_to)}</span>`
                : ""}
              <p>${escapeHtml(message.text)}</p>
              ${message.mentions?.length
                ? `<span class="mentions">${message.mentions.map(name =>
                  `@${escapeHtml(name)}`).join(" ")}</span>`
                : ""}
              ${citationRefs(message.citation_ids)}
            </div>
          </article>`).join("")}
      </div>
    </section>
    <article class="war-room-decision manager-close">
      <p class="eyebrow">MANAGER-LED FINAL DECISION</p>
      <h3>${escapeHtml(decision.decision_owner)} (AI Clone)</h3>
      <p>${escapeHtml(decision.recommendation)}</p>
      <section><h4>Rationale and trade-offs</h4><ul>${decision.rationale_tradeoffs.map(item =>
        `<li>${escapeHtml(item)}</li>`).join("")}</ul></section>
      <section><h4>Dissent</h4><ul>${decision.dissenting_views.map(item =>
        `<li><strong>${escapeHtml(item.name)} (AI Clone):</strong> ${escapeHtml(item.view)}</li>`
      ).join("")}</ul></section>
      <section><h4>Risks and mitigations</h4><ul>${decision.risks_mitigations.map(item =>
        `<li><strong>${escapeHtml(item.risk)}</strong> — ${escapeHtml(item.mitigation)}</li>`
      ).join("")}</ul></section>
      <section><h4>Owners and actions</h4><ul>${decision.action_items.map(item =>
        `<li><strong>${escapeHtml(item.owner)} (AI Clone):</strong> ${escapeHtml(item.action)}</li>`
      ).join("")}</ul></section>
      ${citationMarkup(verifiedCitations)}
    </article>`;
}

function appendMessage(kind, label, content, response = null) {
  const assistant = kind === "assistant";
  const user = kind === "user";
  const name = assistant ? selectedName() : "You";
  const rowClass = assistant ? "" : kind;
  const evidence = response ? citationMarkup(response.citations || []) : "";
  const meta = response
    ? `${response.expert_attributed_citation_count || 0} expert-attributed · ` +
      `${response.contextual_citation_count || 0} contextual`
    : "";
  $("messages").insertAdjacentHTML("beforeend", `
    <div class="message-row ${rowClass}">
      <span class="avatar" style="--avatar-hue:${assistant ? avatarHue(name) : 220}" aria-hidden="true">${assistant ? escapeHtml(initials(name)) : "YO"}</span>
      <div class="message-stack">
        <div class="message-label">${escapeHtml(label)}</div>
        <div class="message">${escapeHtml(content)}</div>
        ${evidence}
        ${meta ? `<div class="message-meta">${escapeHtml(meta)}</div>` : ""}
      </div>
    </div>`);
  if (user) $("messages").scrollTop = $("messages").scrollHeight;
}

async function loadExperts(selectNewest = false) {
  experts = await api("/api/experts");
  $("expertSelect").innerHTML = experts.length
    ? experts.map(expert => `<option value="${expert.id}">${escapeHtml(expert.name)}</option>`).join("")
    : '<option value="">Create an expert to begin</option>';
  if (!experts.length) {
    expertId = null;
  } else {
    expertId = selectNewest ? experts[0].id : (expertId || experts[0].id);
    $("expertSelect").value = expertId;
  }
  updateIdentity();
  resetConversation();
  await Promise.all([refresh(), loadPortfolioSummary()]);
}

async function refresh() {
  if (!expertId) return;
  await Promise.all([loadSources(), loadDecisions(), loadFingerprint()]);
}

async function loadSources() {
  const sources = await api(`/api/experts/${expertId}/sources`);
  $("sourceList").innerHTML = sources.length ? sources.map(source => `
    <article class="source">
      <div class="source-line"><strong>${escapeHtml(source.title)}</strong>
        <span class="badge">${escapeHtml(source.status)}</span></div>
      <div class="muted">${escapeHtml(source.source_type)} · ${source.decision_count} decisions${source.error ? ` · ${escapeHtml(source.error)}` : ""}</div>
    </article>`).join("") : '<div class="empty-state">No sources uploaded yet.</div>';
}

async function loadDecisions() {
  const decisions = await api(`/api/experts/${expertId}/decisions`);
  $("decisionList").innerHTML = decisions.length ? decisions.map(decision => {
    const attributed = decision.evidence_author
      && decision.evidence_author.trim().toLowerCase() === decision.expert.trim().toLowerCase();
    const role = decision.evidence_role ? ` (${decision.evidence_role})` : "";
    const provenance = attributed
      ? `Expert-attributed: ${decision.evidence_author}${role}`
      : decision.evidence_author
        ? `Attributed context: ${decision.evidence_author}${role}`
        : "Unattributed context";
    return `
      <article class="decision">
        <span class="badge ${attributed ? "" : "context"}">${escapeHtml(provenance)}</span>
        <strong>${escapeHtml(decision.choice)}</strong>
        <div>${escapeHtml((decision.rationale || []).join("; ") || "No explicit rationale extracted")}</div>
        <div class="muted">${escapeHtml(decision.source_title)} · ${escapeHtml(decision.page_or_segment)} · ${Math.round(decision.confidence * 100)}% confidence</div>
      </article>`;
  }).join("") : '<div class="empty-state">No decisions extracted yet.</div>';
}

async function loadFingerprint() {
  const fingerprint = await api(`/api/experts/${expertId}/fingerprint`);
  const categories = [
    ["Provenance", [
      `${fingerprint.expert_attributed_decision_count} expert-attributed judgments`,
      `${fingerprint.contextual_decision_count} contextual records`
    ]],
    ["Recurring preferences", fingerprint.recurring_preferences.map(item => item.pattern)],
    ["Tradeoffs", fingerprint.tradeoffs.map(item => item.pattern)],
    ["Risk posture", fingerprint.risk_posture.map(item => item.pattern)],
    ["Technology criteria", fingerprint.technology_criteria.map(item => item.pattern)],
    ["Troubleshooting", fingerprint.troubleshooting_strategies.map(item => item.pattern)],
    ["Operational practices", fingerprint.operational_practices.map(item => item.pattern)],
    ["Outcome-backed lessons", fingerprint.outcome_backed_lessons.map(item => item.pattern)]
  ];
  $("fingerprintGrid").innerHTML = categories.map(([title, items]) => `
    <article class="card"><h3>${escapeHtml(title)}</h3>${items.length
      ? `<ul>${items.map(item => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`
      : '<p class="muted">Not enough attributed evidence yet.</p>'}</article>`).join("");
}

function activateView(viewId) {
  document.querySelectorAll(".tab").forEach(tab => {
    const active = tab.dataset.tab === viewId;
    tab.classList.toggle("active", active);
    tab.setAttribute("aria-selected", String(active));
  });
  document.querySelectorAll(".view").forEach(view => {
    view.hidden = view.id !== viewId;
  });
}

async function selectExpertByName(name) {
  const expert = experts.find(item => item.name === name);
  if (!expert || expert.id === expertId) return;
  expertId = expert.id;
  $("expertSelect").value = expertId;
  updateIdentity();
  resetConversation();
  await refresh();
}

$("expertSelect").addEventListener("change", async event => {
  expertId = event.target.value || null;
  updateIdentity();
  resetConversation();
  await refresh();
});

$("expertForm").addEventListener("submit", async event => {
  event.preventDefault();
  await withBusy(event.currentTarget, "Creating…", async () => {
    try {
      await api("/api/experts", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          name: $("expertName").value,
          description: $("expertDescription").value
        })
      });
      event.currentTarget.reset();
      await loadExperts(true);
      notice("Expert created.");
    } catch (error) {
      notice(error.message, true);
    }
  });
});

$("uploadForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!expertId) return notice("Create an expert first.", true);
  await withBusy(event.currentTarget, "Ingesting…", async () => {
    const data = new FormData();
    data.append("file", $("sourceFile").files[0]);
    data.append("title", $("sourceTitle").value);
    data.append("source_type", $("sourceType").value);
    try {
      const result = await api(`/api/experts/${expertId}/sources`, {method: "POST", body: data});
      event.currentTarget.reset();
      notice(`Ready: ${result.decisions.length} decisions extracted.`);
      await Promise.all([refresh(), loadPortfolioSummary()]);
      activateView("sources");
    } catch (error) {
      notice(error.message, true);
    }
  });
});

$("chatForm").addEventListener("submit", async event => {
  event.preventDefault();
  if (!expertId) return notice("Create or select an expert first.", true);
  const question = $("question").value.trim();
  if (!question) return;
  appendMessage("user", "You", question);
  $("question").value = "";
  await withBusy(event.currentTarget, "Thinking…", async () => {
    try {
      const response = await api(`/api/experts/${expertId}/chat`, {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question, top_k: 5})
      });
      appendMessage("assistant", `${selectedName()} (AI Clone)`, response.answer, response);
      $("evidenceStrength").className = `evidence-strength ${response.evidence_strength}`;
      $("evidenceStrength").textContent = `Evidence: ${response.evidence_strength}`;
      $("messages").scrollTop = $("messages").scrollHeight;
    } catch (error) {
      appendMessage("error", "Unable to answer", error.message);
    }
  });
});

$("warRoomForm").addEventListener("submit", async event => {
  event.preventDefault();
  const topic = $("warRoomTopic").value.trim();
  if (!topic) return;
  $("warRoomResult").innerHTML = '<div class="empty-state">Preparing the evidence-grounded panel…</div>';
  await withBusy(event.currentTarget, "Running one Azure call…", async () => {
    try {
      const response = await api("/api/war-room", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({topic})
      });
      renderWarRoom(response);
    } catch (error) {
      $("warRoomResult").innerHTML =
        `<div class="empty-state war-room-error">${escapeHtml(error.message)}</div>`;
    }
  });
});

$("expertFinderForm").addEventListener("submit", async event => {
  event.preventDefault();
  const question = $("expertFinderQuestion").value.trim();
  if (!question) return;
  $("expertFinderResult").innerHTML =
    '<div class="empty-state">Comparing attributable decisions across all AI Clones…</div>';
  await withBusy(event.currentTarget, "Ranking evidence…", async () => {
    try {
      const response = await api("/api/expert-finder", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({question, top_k: 5})
      });
      renderExpertMatches(response);
    } catch (error) {
      $("expertFinderResult").innerHTML =
        `<div class="empty-state expert-finder-error">${escapeHtml(error.message)}</div>`;
    }
  });
});

$("expertFinderResult").addEventListener("click", async event => {
  const button = event.target.closest(".ask-matched-expert");
  if (!button) return;
  await selectExpertByName(button.dataset.expertName);
  $("question").value = $("expertFinderQuestion").value.trim();
  activateView("chat");
  $("question").focus();
});

document.querySelectorAll("[data-expert-query]").forEach(button => {
  button.addEventListener("click", () => {
    $("expertFinderQuestion").value = button.dataset.expertQuery;
    $("expertFinderForm").requestSubmit();
  });
});

document.querySelectorAll(".tab").forEach(tab => {
  tab.addEventListener("click", () => activateView(tab.dataset.tab));
});

document.querySelectorAll(".project-filter").forEach(filter => {
  filter.setAttribute("aria-pressed", String(filter.classList.contains("active")));
  filter.addEventListener("click", () => {
    const project = filter.dataset.project;
    document.querySelectorAll(".project-filter").forEach(item => {
      const active = item === filter;
      item.classList.toggle("active", active);
      item.setAttribute("aria-pressed", String(active));
    });
    document.querySelectorAll(".scenario-card").forEach(card => {
      card.hidden = project !== "all"
        && card.dataset.project !== project
        && card.dataset.project !== "cross";
    });
  });
});

document.querySelectorAll(".scenario-card").forEach(card => {
  card.addEventListener("click", async () => {
    if (card.dataset.expert) await selectExpertByName(card.dataset.expert);
    if (card.dataset.view === "warRoom") {
      $("warRoomTopic").value = card.dataset.prompt;
      activateView("warRoom");
      $("warRoomTopic").focus();
      return;
    }
    $("question").value = card.dataset.prompt;
    activateView("chat");
    $("question").focus();
  });
});

$("overviewComposer").addEventListener("click", () => {
  activateView("chat");
  $("question").focus();
});

loadExperts().catch(error => notice(error.message, true));
