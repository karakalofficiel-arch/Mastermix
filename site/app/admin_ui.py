"""Backoffice /admin de mastermix.fr : une page HTML/CSS/JS statique, sans dépendance externe.

Toute la logique passe par /admin/api/... (JSON). Le jeton CSRF renvoyé à la
connexion est envoyé dans l'en-tête X-CSRF sur chaque écriture.
"""

PAGE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Administration — MasterMix</title>
<link rel="icon" type="image/svg+xml" href="/logo.svg">
<style>
:root{--apple:#a4de02;--apple-light:#c6f04a;--bg:#0a0a0a;--panel:#121212;--panel2:#181818;--line:#262626;--text:#ecece6;--muted:#a8a8a0;--dim:#8f8f88;--rouge:#ff6b6b;--vert:#7fae00}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.5 system-ui,"Segoe UI",sans-serif}
a{color:var(--apple-light)}
button,input,select,textarea{font:inherit;color:inherit}
input,select,textarea{width:100%;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:9px 11px;color:var(--text)}
input:focus,textarea:focus,select:focus{outline:2px solid var(--apple);outline-offset:0;border-color:var(--apple)}
textarea{min-height:110px;resize:vertical;font-family:inherit}
textarea.md{min-height:360px;font-family:Consolas,"Cascadia Mono",ui-monospace,monospace;font-size:13.5px}
label{display:block;font-size:13px;color:var(--muted);margin:12px 0 4px}
button{cursor:pointer;border:1px solid var(--line);background:var(--panel2);color:var(--text);padding:9px 14px;border-radius:8px}
button:hover{border-color:var(--apple)}
button.p{background:var(--apple);color:var(--bg);border-color:var(--apple);font-weight:700}
button.p:hover{background:var(--apple-light)}
button.danger{color:var(--rouge)}
button:disabled{opacity:.5;cursor:default}
.hidden{display:none!important}
header{display:flex;align-items:center;gap:14px;padding:12px 20px;border-bottom:1px solid var(--line);background:var(--panel);position:sticky;top:0;z-index:3}
header img{width:30px;height:30px;border-radius:7px}
header b{font-size:16px}
header nav{display:flex;gap:4px;margin-left:16px;flex-wrap:wrap}
header nav button{border:0;background:transparent;color:var(--muted);padding:8px 12px}
header nav button.on{color:var(--apple);background:var(--panel2)}
header .droite{margin-left:auto;display:flex;gap:8px;align-items:center;font-size:13px;color:var(--dim)}
main{max-width:1180px;margin:0 auto;padding:24px 20px 80px}
h2{margin:0 0 16px;font-size:22px}
h3{margin:22px 0 8px;font-size:16px;color:var(--apple)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px;margin-bottom:18px}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}
.row>*{flex:1 1 200px}
.row>.auto{flex:0 0 auto}
.actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:16px}
table{width:100%;border-collapse:collapse;font-size:14px}
th,td{text-align:left;padding:9px 8px;border-bottom:1px solid var(--line);vertical-align:top}
th{color:var(--dim);font-weight:500}
tr.nonlu td{font-weight:600}
tr.clic{cursor:pointer}
tr.clic:hover td{background:var(--panel2)}
.mono{font-family:Consolas,"Cascadia Mono",ui-monospace,monospace;font-size:12.5px;word-break:break-all}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%);background:var(--panel2);border:1px solid var(--apple);padding:10px 16px;border-radius:10px;z-index:9;max-width:90vw}
.toast.err{border-color:var(--rouge)}
.login{max-width:380px;margin:12vh auto}
.login img{width:56px;height:56px;border-radius:12px;display:block;margin:0 auto 12px}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
@media(max-width:800px){.grid2{grid-template-columns:1fr}}
.msg{white-space:pre-wrap;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:14px;max-height:60vh;overflow:auto}
.msg-html{background:#f6f6f2;color:#111;border-radius:8px;padding:14px;max-height:60vh;overflow:auto}
.msg-html a{color:#2a5db0}
.pill{display:inline-block;padding:2px 8px;border-radius:99px;font-size:12px;background:var(--panel2);border:1px solid var(--line);color:var(--muted)}
.pill.ok{color:var(--apple);border-color:var(--vert)}
progress{width:100%;height:8px}
.journal{font-family:Consolas,ui-monospace,monospace;font-size:12px;white-space:pre;overflow:auto;max-height:50vh;background:var(--bg);padding:12px;border-radius:8px;border:1px solid var(--line)}
.aide{font-size:13px;color:var(--dim)}
</style>
</head>
<body>
<div id="login" class="login hidden">
  <div class="card">
    <img src="/logo.svg" alt="">
    <h2 style="text-align:center">Administration MasterMix</h2>
    <form id="form-login">
      <label>Mot de passe</label>
      <input type="password" id="mdp" autocomplete="current-password" autofocus>
      <div class="actions"><button class="p" type="submit" style="flex:1">Se connecter</button></div>
    </form>
  </div>
</div>

<div id="app" class="hidden">
<header>
  <img src="/logo.svg" alt=""><b>MasterMix</b>
  <nav id="onglets">
    <button data-t="contenu" class="on">Contenu</button>
    <button data-t="pages">Pages</button>
    <button data-t="fichiers">Fichiers</button>
    <button data-t="courrier">Courrier</button>
    <button data-t="adresses">Adresses</button>
    <button data-t="reglages">Réglages</button>
  </nav>
  <div class="droite"><a href="/" target="_blank">Voir le site</a><button id="deco">Déconnexion</button></div>
</header>
<main>

<section id="t-contenu">
  <h2>Contenu de la page d'accueil</h2>
  <p class="aide">Chaque modification est visible en ligne dès l'enregistrement. Une sauvegarde horodatée est conservée à chaque enregistrement (onglet Réglages).</p>
  <div id="contenu-form"></div>
  <div class="actions"><button class="p" id="contenu-save">Enregistrer le contenu</button></div>
</section>

<section id="t-pages" class="hidden">
  <h2>Pages libres</h2>
  <div class="grid2">
    <div class="card">
      <table id="pages-liste"><thead><tr><th>Titre</th><th>Adresse</th><th>Visible</th><th>Ordre</th></tr></thead><tbody></tbody></table>
      <div class="actions"><button id="page-nouvelle">Nouvelle page</button></div>
    </div>
    <div class="card" id="page-edit">
      <div class="row">
        <div><label>Titre</label><input id="page-titre"></div>
        <div><label>Adresse (slug)</label><input id="page-slug" placeholder="actualites"></div>
      </div>
      <div class="row">
        <div class="auto"><label>Visible dans le menu</label><select id="page-visible"><option value="1">Oui</option><option value="0">Non</option></select></div>
        <div class="auto"><label>Ordre</label><input id="page-ordre" type="number" value="0" style="width:90px"></div>
      </div>
      <label>Contenu (Markdown simplifié : # titres, - listes, **gras**, *italique*, [lien](url), ![image](media/nom.jpg), ---)</label>
      <textarea id="page-md" class="md"></textarea>
      <div class="actions"><button class="p" id="page-save">Enregistrer la page</button><a id="page-voir" href="#" target="_blank" class="hidden"><button type="button">Voir</button></a><button class="danger" id="page-suppr">Supprimer</button></div>
    </div>
  </div>
</section>

<section id="t-fichiers" class="hidden">
  <h2>Fichiers</h2>
  <div class="grid2">
    <div class="card">
      <h3>Images (media/) — 8 Mo max</h3>
      <input type="file" id="up-media" accept=".png,.jpg,.jpeg,.webp,.gif,.svg">
      <progress id="pg-media" value="0" max="100" class="hidden"></progress>
      <table id="liste-media"><thead><tr><th>Nom</th><th>Taille</th><th></th></tr></thead><tbody></tbody></table>
      <p class="aide">Dans une page : <span class="mono">![légende](media/nom.jpg)</span>. Dans l'accueil : nom du fichier dans « capture ».</p>
    </div>
    <div class="card">
      <h3>Téléchargements — 200 Mo max</h3>
      <input type="file" id="up-telechargements" accept=".exe,.zip,.msi">
      <progress id="pg-telechargements" value="0" max="100" class="hidden"></progress>
      <table id="liste-telechargements"><thead><tr><th>Nom</th><th>Taille</th><th>SHA-256</th><th></th></tr></thead><tbody></tbody></table>
      <p class="aide">Après un envoi, le bouton « Utiliser » remplit fichier, taille et empreinte de la section Téléchargement.</p>
    </div>
  </div>
</section>

<section id="t-courrier" class="hidden">
  <h2>Courrier</h2>
  <div class="row card" style="align-items:center">
    <div><label>Boîte</label><select id="c-boite"></select></div>
    <div class="auto"><label>Dossier</label><select id="c-dossier"><option value="recus">Reçus</option><option value="envoyes">Envoyés</option></select></div>
    <div class="auto"><label>&nbsp;</label><button id="c-rafraichir">Rafraîchir</button></div>
    <div class="auto"><label>&nbsp;</label><button class="p" id="c-nouveau">Nouveau message</button></div>
  </div>
  <div class="grid2">
    <div class="card" style="padding:0;overflow:auto;max-height:75vh">
      <table id="c-liste"><thead><tr><th>De / À</th><th>Objet</th><th>Date</th></tr></thead><tbody></tbody></table>
    </div>
    <div class="card" id="c-lecture"><p class="aide">Choisis un message.</p></div>
  </div>
  <div class="card hidden" id="c-compose">
    <h3 id="c-compose-titre">Nouveau message</h3>
    <div class="row"><div><label>À</label><input id="c-a" placeholder="adresse@exemple.fr, autre@exemple.fr"></div><div><label>Cc</label><input id="c-cc"></div></div>
    <label>Objet</label><input id="c-sujet">
    <label>Message</label><textarea id="c-texte" class="md" style="min-height:220px;font-family:inherit"></textarea>
    <label>Pièces jointes (20 Mo max au total)</label><input type="file" id="c-pieces" multiple>
    <div class="actions"><button class="p" id="c-envoyer">Envoyer</button><button id="c-annuler">Annuler</button></div>
  </div>
</section>

<section id="t-adresses" class="hidden">
  <h2>Adresses @mastermix.fr</h2>
  <div class="grid2">
    <div class="card">
      <h3>Boîtes</h3>
      <table id="a-liste"><thead><tr><th>Adresse</th><th>Nom</th><th>Quota</th><th>Admin</th><th></th></tr></thead><tbody></tbody></table>
      <h3>Créer une boîte</h3>
      <div class="row"><div><label>Adresse</label><div style="display:flex;align-items:center;gap:6px"><input id="a-local" placeholder="prenom" style="flex:1"><span>@mastermix.fr</span></div></div><div><label>Nom affiché</label><input id="a-nom"></div></div>
      <div class="row"><div><label>Mot de passe (vide = généré)</label><input id="a-mdp" type="text" autocomplete="off"></div><div class="auto"><label>Quota (Go)</label><input id="a-quota" type="number" value="1" min="1" style="width:90px"></div></div>
      <div class="actions"><button class="p" id="a-creer">Créer la boîte</button></div>
    </div>
    <div class="card">
      <h3>Alias</h3>
      <table id="al-liste"><thead><tr><th>Alias</th><th>Vers</th><th></th></tr></thead><tbody></tbody></table>
      <div class="row"><div><label>Alias</label><div style="display:flex;align-items:center;gap:6px"><input id="al-local" placeholder="support" style="flex:1"><span>@mastermix.fr</span></div></div><div><label>Destinations</label><input id="al-dest" placeholder="contact@mastermix.fr"></div></div>
      <div class="actions"><button class="p" id="al-creer">Créer l'alias</button></div>
      <p class="aide">Les boîtes créées ici sont ouvrables dans l'onglet Courrier. Une boîte créée ailleurs se rattache avec son mot de passe (bouton « Rattacher »). Webmail pour les personnes : <a href="https://mail.besancon.vip/webmail" target="_blank">mail.besancon.vip/webmail</a>.</p>
    </div>
  </div>
</section>

<section id="t-reglages" class="hidden">
  <h2>Réglages</h2>
  <div class="grid2">
    <div class="card">
      <h3>Mot de passe administrateur</h3>
      <label>Ancien</label><input id="r-ancien" type="password" autocomplete="current-password">
      <label>Nouveau (12 caractères minimum)</label><input id="r-nouveau" type="password" autocomplete="new-password">
      <div class="actions"><button class="p" id="r-mdp">Changer</button></div>
      <h3>Serveur de courrier (Mailu)</h3>
      <label>URL de l'API Mailu</label><input id="r-mailu-url" placeholder="http://192.168.1.166:8080/api/v1">
      <label>Jeton API (laisser vide pour conserver l'actuel) <span id="r-jeton-etat" class="pill"></span></label><input id="r-mailu-jeton" type="password" autocomplete="off">
      <div class="row"><div><label>Hôte IMAP/SMTP</label><input id="r-hote"></div><div><label>Nom du certificat</label><input id="r-cert"></div></div>
      <div class="actions"><button class="p" id="r-save">Enregistrer</button><button id="r-tester">Tester l'API</button></div>
    </div>
    <div class="card">
      <h3>Sauvegardes du contenu</h3>
      <table id="r-sauvegardes"><tbody></tbody></table>
      <h3>Journal</h3>
      <div id="r-journal" class="journal"></div>
    </div>
  </div>
</section>
</main>
</div>

<script>
(function(){
'use strict';
var csrf = null, etat = {}, contenu = null, pageCourante = null, boiteCourante = null, msgCourant = null;
var $ = function(id){ return document.getElementById(id); };
var esc = function(s){ return String(s == null ? '' : s).replace(/[&<>"']/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]; }); };
var taille = function(o){ o = +o || 0; return o >= 1048576 ? Math.round(o/1048576) + ' Mo' : o >= 1024 ? Math.round(o/1024) + ' Ko' : o + ' o'; };
var toastT = null;
function toast(m, err){ var t = document.querySelector('.toast'); if (t) t.remove(); t = document.createElement('div'); t.className = 'toast' + (err ? ' err' : ''); t.textContent = m; document.body.appendChild(t); clearTimeout(toastT); toastT = setTimeout(function(){ t.remove(); }, err ? 7000 : 3000); }
function api(methode, chemin, corps, brut){
  var o = {method: methode, headers: {}, credentials: 'same-origin'};
  if (csrf) o.headers['X-CSRF'] = csrf;
  if (corps !== undefined) { if (brut) { o.body = corps; } else { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(corps); } }
  return fetch('/admin/api' + chemin, o).then(function(r){
    if (r.status === 401) { montrerLogin(); throw new Error('Session expirée, reconnectez-vous.'); }
    return r.text().then(function(t){ var d = {}; try { d = t ? JSON.parse(t) : {}; } catch(e) { d = {erreur: t}; } if (!r.ok) throw new Error(d.erreur || ('Erreur ' + r.status)); return d; });
  });
}
function erreur(e){ toast(e.message || String(e), true); }

/* --- connexion ------------------------------------------------------- */
function montrerLogin(){ $('app').classList.add('hidden'); $('login').classList.remove('hidden'); csrf = null; $('mdp').focus(); }
function montrerApp(){ $('login').classList.add('hidden'); $('app').classList.remove('hidden'); }
$('form-login').addEventListener('submit', function(ev){ ev.preventDefault();
  api('POST', '/connexion', {mot_de_passe: $('mdp').value}).then(function(d){ csrf = d.csrf; $('mdp').value = ''; demarrer(); }).catch(erreur); });
$('deco').addEventListener('click', function(){ api('POST', '/deconnexion', {}).then(montrerLogin).catch(montrerLogin); });
function demarrer(){ api('GET', '/etat').then(function(d){ csrf = d.csrf; etat = d; montrerApp(); if (d.mot_de_passe_initial) toast('Mot de passe initial en service : changez-le dans Réglages.', true); onglet('contenu'); }).catch(function(){ montrerLogin(); }); }

/* --- onglets --------------------------------------------------------- */
var chargeurs = {contenu: chargerContenu, pages: chargerPages, fichiers: chargerFichiers, courrier: chargerCourrier, adresses: chargerAdresses, reglages: chargerReglages};
function onglet(nom){
  document.querySelectorAll('#onglets button').forEach(function(b){ b.classList.toggle('on', b.dataset.t === nom); });
  document.querySelectorAll('main > section').forEach(function(s){ s.classList.toggle('hidden', s.id !== 't-' + nom); });
  chargeurs[nom]();
}
$('onglets').addEventListener('click', function(ev){ var b = ev.target.closest('button'); if (b) onglet(b.dataset.t); });

/* --- contenu --------------------------------------------------------- */
var LIBELLES = {site: 'Site', accueil: 'Accueil', promesses: 'Trois promesses', console: 'Section console', telechargement: 'Téléchargement', configuration: 'Configuration requise', pied: 'Pied de page'};
function champ(section, cle, valeur){
  var id = 'f-' + section + '-' + cle, long = typeof valeur === 'string' && valeur.length > 90;
  return '<label>' + esc(cle) + '</label>' + (long ? '<textarea id="' + id + '">' + esc(valeur) + '</textarea>' : '<input id="' + id + '" value="' + esc(valeur) + '">');
}
function chargerContenu(){
  api('GET', '/contenu').then(function(d){
    contenu = d.contenu; var h = '';
    d.champs && Object.keys(d.champs).forEach(function(section){
      h += '<div class="card"><h3>' + esc(LIBELLES[section] || section) + '</h3>';
      d.champs[section].forEach(function(cle){
        var v = contenu[section][cle];
        if (cle === 'cartes') { v.forEach(function(c, i){ h += '<div class="row"><div>' + champ(section, 'cartes.' + i + '.titre', c.titre) + '</div><div style="flex:3 1 300px">' + champ(section, 'cartes.' + i + '.texte', c.texte) + '</div></div>'; }); }
        else if (cle === 'points') { h += '<label>points (une ligne par point)</label><textarea id="f-console-points">' + esc(v.join('\n')) + '</textarea>'; }
        else if (cle === 'lignes') { h += '<label>lignes (libellé | valeur, une par ligne)</label><textarea id="f-configuration-lignes">' + esc(v.map(function(l){ return l[0] + ' | ' + l[1]; }).join('\n')) + '</textarea>'; }
        else h += champ(section, cle, v);
      });
      h += '</div>';
    });
    $('contenu-form').innerHTML = h;
  }).catch(erreur);
}
function lireContenu(){
  var c = JSON.parse(JSON.stringify(contenu));
  document.querySelectorAll('#contenu-form [id^="f-"]').forEach(function(el){
    var p = el.id.slice(2).split('-'), section = p[0], cle = p.slice(1).join('-');
    if (cle === 'points') c.console.points = el.value.split('\n').map(function(s){ return s.trim(); }).filter(Boolean);
    else if (cle === 'lignes') c.configuration.lignes = el.value.split('\n').map(function(s){ var i = s.indexOf('|'); return i < 0 ? null : [s.slice(0, i).trim(), s.slice(i + 1).trim()]; }).filter(Boolean);
    else if (cle.indexOf('cartes.') === 0) { var q = cle.split('.'); c[section].cartes[+q[1]][q[2]] = el.value; }
    else if (cle === 'taille') c[section][cle] = parseInt(el.value, 10) || 0;
    else c[section][cle] = el.value;
  });
  return c;
}
$('contenu-save').addEventListener('click', function(){ api('PUT', '/contenu', lireContenu()).then(function(){ toast('Contenu enregistré, en ligne.'); chargerContenu(); }).catch(erreur); });

/* --- pages ----------------------------------------------------------- */
function chargerPages(){
  api('GET', '/pages').then(function(d){
    $('pages-liste').querySelector('tbody').innerHTML = d.pages.map(function(p){ return '<tr class="clic" data-slug="' + esc(p.slug) + '"><td>' + esc(p.titre) + '</td><td class="mono">/p/' + esc(p.slug) + '</td><td>' + (p.visible ? 'oui' : 'non') + '</td><td>' + p.ordre + '</td></tr>'; }).join('') || '<tr><td colspan="4" class="aide">Aucune page.</td></tr>';
  }).catch(erreur);
}
$('pages-liste').addEventListener('click', function(ev){ var tr = ev.target.closest('tr[data-slug]'); if (!tr) return; api('GET', '/pages/' + tr.dataset.slug).then(editerPage).catch(erreur); });
function editerPage(p){ pageCourante = p; $('page-titre').value = p.titre || ''; $('page-slug').value = p.slug || ''; $('page-visible').value = p.visible ? '1' : '0'; $('page-ordre').value = p.ordre || 0; $('page-md').value = p.contenu_md || ''; $('page-voir').classList.toggle('hidden', !p.slug); $('page-voir').href = '/p/' + (p.slug || ''); }
$('page-nouvelle').addEventListener('click', function(){ editerPage({titre: '', slug: '', visible: true, ordre: 0, contenu_md: '# Titre\n\nTexte.'}); $('page-titre').focus(); });
$('page-save').addEventListener('click', function(){
  var slug = $('page-slug').value.trim().toLowerCase();
  if (!slug) { slug = $('page-titre').value.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 60); $('page-slug').value = slug; }
  api('PUT', '/pages/' + slug, {titre: $('page-titre').value, slug: slug, visible: $('page-visible').value === '1', ordre: parseInt($('page-ordre').value, 10) || 0, contenu_md: $('page-md').value})
    .then(function(){ toast('Page enregistrée.'); chargerPages(); api('GET', '/pages/' + slug).then(editerPage); }).catch(erreur);
});
$('page-suppr').addEventListener('click', function(){ var slug = $('page-slug').value.trim(); if (!slug || !confirm('Supprimer la page /p/' + slug + ' ?')) return; api('DELETE', '/pages/' + slug).then(function(){ toast('Page supprimée.'); editerPage({}); chargerPages(); }).catch(erreur); });
editerPage({});

/* --- fichiers -------------------------------------------------------- */
function chargerFichiers(){ ['media', 'telechargements'].forEach(function(cat){
  api('GET', '/fichiers/' + cat).then(function(d){
    $('liste-' + cat).querySelector('tbody').innerHTML = d.fichiers.map(function(f){
      return '<tr><td><a href="/' + cat + '/' + encodeURIComponent(f.nom) + '" target="_blank">' + esc(f.nom) + '</a></td><td>' + taille(f.taille) + '</td>' + (cat === 'telechargements' ? '<td class="mono">' + esc((f.sha256 || '').slice(0, 16)) + '…</td>' : '') +
        '<td style="white-space:nowrap">' + (cat === 'telechargements' ? '<button data-util="' + esc(f.nom) + '" data-taille="' + f.taille + '" data-sha="' + esc(f.sha256 || '') + '">Utiliser</button> ' : '') + '<button class="danger" data-suppr="' + esc(f.nom) + '" data-cat="' + cat + '">Supprimer</button></td></tr>';
    }).join('') || '<tr><td colspan="4" class="aide">Aucun fichier.</td></tr>';
  }).catch(erreur);
}); }
document.querySelector('#t-fichiers').addEventListener('click', function(ev){
  var b = ev.target.closest('button'); if (!b) return;
  if (b.dataset.suppr) { if (!confirm('Supprimer ' + b.dataset.suppr + ' ?')) return; api('DELETE', '/fichiers/' + b.dataset.cat + '/' + encodeURIComponent(b.dataset.suppr)).then(function(){ toast('Supprimé.'); chargerFichiers(); }).catch(erreur); }
  if (b.dataset.util) { api('GET', '/contenu').then(function(d){ var c = d.contenu; c.telechargement.fichier = b.dataset.util; c.telechargement.taille = +b.dataset.taille; c.telechargement.sha256 = b.dataset.sha; return api('PUT', '/contenu', c); }).then(function(){ toast('Section Téléchargement mise à jour.'); }).catch(erreur); }
});
function televerser(cat, fichier){
  var MORCEAU = 1048576, total = Math.ceil(fichier.size / MORCEAU) || 1, id = Math.random().toString(36).slice(2) + Date.now().toString(36), pg = $('pg-' + cat);
  pg.classList.remove('hidden'); pg.value = 0;
  var suite = function(i){
    if (i >= total) return;
    var bloc = fichier.slice(i * MORCEAU, (i + 1) * MORCEAU);
    return fetch('/admin/api/fichiers/' + cat + '/morceau?nom=' + encodeURIComponent(fichier.name) + '&id=' + id + '&indice=' + i + '&total=' + total, {method: 'POST', credentials: 'same-origin', headers: {'X-CSRF': csrf, 'Content-Type': 'application/octet-stream'}, body: bloc})
      .then(function(r){ return r.json().then(function(d){ if (!r.ok) throw new Error(d.erreur || 'Erreur ' + r.status); return d; }); })
      .then(function(d){ pg.value = Math.round((i + 1) / total * 100); if (i + 1 < total) return suite(i + 1); toast('Fichier reçu : ' + d.nom + (d.sha256 ? ' · SHA-256 ' + d.sha256.slice(0, 12) + '…' : '')); pg.classList.add('hidden'); chargerFichiers(); });
  };
  return suite(0).catch(function(e){ pg.classList.add('hidden'); erreur(e); });
}
$('up-media').addEventListener('change', function(){ if (this.files[0]) televerser('media', this.files[0]); this.value = ''; });
$('up-telechargements').addEventListener('change', function(){ if (this.files[0]) televerser('telechargements', this.files[0]); this.value = ''; });

/* --- adresses -------------------------------------------------------- */
function chargerAdresses(){
  api('GET', '/adresses').then(function(d){
    $('a-liste').querySelector('tbody').innerHTML = d.boites.map(function(b){
      return '<tr><td class="mono">' + esc(b.email) + '</td><td>' + esc(b.nom) + '</td><td>' + taille(b.utilise) + ' / ' + taille(b.quota) + '</td><td>' + (b.ouvrable ? '<span class="pill ok">ouvrable</span>' : '<span class="pill">non rattachée</span>') + '</td>' +
        '<td style="white-space:nowrap">' + (b.ouvrable ? '' : '<button data-rattacher="' + esc(b.email) + '">Rattacher</button> ') + '<button data-reset="' + esc(b.email) + '">Nouveau mot de passe</button> <button class="danger" data-supprimer="' + esc(b.email) + '">Supprimer</button></td></tr>';
    }).join('') || '<tr><td colspan="5" class="aide">Aucune boîte.</td></tr>';
    $('al-liste').querySelector('tbody').innerHTML = d.alias.map(function(a){ return '<tr><td class="mono">' + esc(a.email) + '</td><td class="mono">' + esc(a.destinations.join(', ')) + '</td><td><button class="danger" data-alias="' + esc(a.email) + '">Supprimer</button></td></tr>'; }).join('') || '<tr><td colspan="3" class="aide">Aucun alias.</td></tr>';
  }).catch(erreur);
}
$('a-creer').addEventListener('click', function(){
  api('POST', '/adresses', {local: $('a-local').value.trim().toLowerCase(), nom: $('a-nom').value, mot_de_passe: $('a-mdp').value, quota: (parseInt($('a-quota').value, 10) || 1) * 1073741824})
    .then(function(d){ toast('Boîte créée : ' + d.email + (d.mot_de_passe ? ' — mot de passe : ' + d.mot_de_passe : '')); $('a-local').value = $('a-nom').value = $('a-mdp').value = ''; chargerAdresses(); if (d.mot_de_passe) prompt('Mot de passe de ' + d.email + ' (copiez-le, il ne sera plus affiché) :', d.mot_de_passe); }).catch(erreur);
});
$('al-creer').addEventListener('click', function(){ api('POST', '/alias', {local: $('al-local').value.trim().toLowerCase(), destinations: $('al-dest').value.split(/[,;\s]+/)}).then(function(){ toast('Alias créé.'); $('al-local').value = $('al-dest').value = ''; chargerAdresses(); }).catch(erreur); });
document.querySelector('#t-adresses').addEventListener('click', function(ev){
  var b = ev.target.closest('button'); if (!b) return;
  if (b.dataset.rattacher) { var m = prompt('Mot de passe de ' + b.dataset.rattacher + ' :'); if (m) api('POST', '/adresses/' + encodeURIComponent(b.dataset.rattacher) + '/rattacher', {mot_de_passe: m}).then(function(){ toast('Boîte rattachée.'); chargerAdresses(); }).catch(erreur); }
  if (b.dataset.reset) { if (!confirm('Générer un nouveau mot de passe pour ' + b.dataset.reset + ' ? L\'ancien cessera de fonctionner.')) return; api('POST', '/adresses/' + encodeURIComponent(b.dataset.reset) + '/mot-de-passe', {}).then(function(d){ prompt('Nouveau mot de passe de ' + b.dataset.reset + ' :', d.mot_de_passe); chargerAdresses(); }).catch(erreur); }
  if (b.dataset.supprimer) { if (prompt('Pour supprimer la boîte et TOUS ses messages, tapez son adresse :') !== b.dataset.supprimer) return; api('DELETE', '/adresses/' + encodeURIComponent(b.dataset.supprimer)).then(function(){ toast('Boîte supprimée.'); chargerAdresses(); }).catch(erreur); }
  if (b.dataset.alias) { if (!confirm('Supprimer l\'alias ' + b.dataset.alias + ' ?')) return; api('DELETE', '/alias/' + encodeURIComponent(b.dataset.alias)).then(function(){ toast('Alias supprimé.'); chargerAdresses(); }).catch(erreur); }
});

/* --- courrier -------------------------------------------------------- */
function chargerCourrier(){
  api('GET', '/adresses/ouvrables').then(function(d){
    var sel = $('c-boite'); var avant = sel.value;
    sel.innerHTML = d.boites.map(function(b){ return '<option value="' + esc(b.email) + '">' + esc(b.email) + '</option>'; }).join('');
    if (!d.boites.length) { $('c-liste').querySelector('tbody').innerHTML = '<tr><td colspan="3" class="aide">Aucune boîte ouvrable : créez ou rattachez une boîte dans Adresses.</td></tr>'; return; }
    sel.value = avant && d.boites.some(function(b){ return b.email === avant; }) ? avant : d.boites[0].email;
    listerMessages();
  }).catch(erreur);
}
function listerMessages(){
  boiteCourante = $('c-boite').value; if (!boiteCourante) return;
  var dossier = $('c-dossier').value;
  $('c-liste').querySelector('tbody').innerHTML = '<tr><td colspan="3" class="aide">Chargement…</td></tr>';
  api('GET', '/courrier/' + encodeURIComponent(boiteCourante) + '/' + dossier).then(function(d){
    $('c-liste').querySelector('tbody').innerHTML = d.messages.map(function(m){ return '<tr class="clic' + (m.lu ? '' : ' nonlu') + '" data-id="' + m.id + '"><td>' + esc(dossier === 'envoyes' ? m.a : m.de) + '</td><td>' + esc(m.sujet) + '</td><td style="white-space:nowrap">' + esc(m.date) + '</td></tr>'; }).join('') || '<tr><td colspan="3" class="aide">Aucun message.</td></tr>';
  }).catch(function(e){ $('c-liste').querySelector('tbody').innerHTML = '<tr><td colspan="3" class="aide">' + esc(e.message) + '</td></tr>'; });
}
$('c-boite').addEventListener('change', listerMessages); $('c-dossier').addEventListener('change', listerMessages); $('c-rafraichir').addEventListener('click', listerMessages);
$('c-liste').addEventListener('click', function(ev){ var tr = ev.target.closest('tr[data-id]'); if (!tr) return; lireMessage(tr.dataset.id); });
function lireMessage(id){
  var dossier = $('c-dossier').value;
  api('GET', '/courrier/' + encodeURIComponent(boiteCourante) + '/' + dossier + '/' + id).then(function(m){
    msgCourant = m;
    var base = '/admin/api/courrier/' + encodeURIComponent(boiteCourante) + '/' + dossier + '/' + id;
    var h = '<h3 style="margin-top:0">' + esc(m.sujet || '(sans objet)') + '</h3><p class="aide">De : ' + esc(m.de) + '<br>À : ' + esc(m.a) + (m.cc ? '<br>Cc : ' + esc(m.cc) : '') + '<br>' + esc(m.date) + '</p>';
    if (m.pieces.length) h += '<p>' + m.pieces.map(function(p){ return '<a href="' + base + '/piece/' + p.indice + '">' + esc(p.nom) + '</a> <span class="aide">(' + taille(p.taille) + ')</span>'; }).join(' · ') + '</p>';
    h += m.texte ? '<div class="msg">' + esc(m.texte) + '</div>' : (m.html ? '<div class="msg-html">' + m.html + '</div>' : '<p class="aide">Message vide.</p>');
    if (m.texte && m.html) h += '<p><a href="#" id="c-voir-html">Afficher la version HTML</a></p><div class="msg-html hidden" id="c-html">' + m.html + '</div>';
    h += '<div class="actions"><button class="p" id="c-repondre">Répondre</button><button id="c-transferer">Transférer</button><button id="c-nonlu">Marquer non lu</button><button class="danger" id="c-supprimer">Supprimer</button></div>';
    $('c-lecture').innerHTML = h;
    var vh = $('c-voir-html'); if (vh) vh.addEventListener('click', function(ev){ ev.preventDefault(); $('c-html').classList.toggle('hidden'); });
    $('c-repondre').addEventListener('click', function(){ composer('Re: ' + (m.sujet || ''), m.de, '\n\n' + m.citation, m.message_id, m.references); });
    $('c-transferer').addEventListener('click', function(){ composer('Fwd: ' + (m.sujet || ''), '', '\n\n---------- Message transféré ----------\nDe : ' + m.de + '\nDate : ' + m.date + '\nObjet : ' + m.sujet + '\n\n' + m.texte, null, null, true); });
    $('c-nonlu').addEventListener('click', function(){ api('POST', base + '/lu', {lu: false}).then(listerMessages).catch(erreur); });
    $('c-supprimer').addEventListener('click', function(){ if (!confirm('Supprimer ce message ?')) return; api('DELETE', base).then(function(){ $('c-lecture').innerHTML = '<p class="aide">Message supprimé.</p>'; listerMessages(); }).catch(erreur); });
    listerMessages();
  }).catch(erreur);
}
var compose = {};
function composer(sujet, a, texte, enReponseA, references, transfert){
  compose = {en_reponse_a: enReponseA || null, references: references || null, transfert: !!transfert, source: transfert && msgCourant ? {dossier: $('c-dossier').value, id: msgCourant.id} : null};
  $('c-compose-titre').textContent = enReponseA ? 'Répondre' : (transfert ? 'Transférer' : 'Nouveau message');
  $('c-a').value = a || ''; $('c-cc').value = ''; $('c-sujet').value = sujet || ''; $('c-texte').value = texte || ''; $('c-pieces').value = '';
  $('c-compose').classList.remove('hidden'); $('c-compose').scrollIntoView({behavior: 'smooth'}); $('c-a').focus();
}
$('c-nouveau').addEventListener('click', function(){ composer('', '', ''); });
$('c-annuler').addEventListener('click', function(){ $('c-compose').classList.add('hidden'); });
function lireFichiers(input){
  var fichiers = Array.prototype.slice.call(input.files || []);
  return Promise.all(fichiers.map(function(f){ return new Promise(function(res, rej){ var r = new FileReader(); r.onload = function(){ res({nom: f.name, type: f.type || 'application/octet-stream', b64: r.result.split(',')[1]}); }; r.onerror = rej; r.readAsDataURL(f); }); }));
}
$('c-envoyer').addEventListener('click', function(){
  var b = $('c-envoyer'); b.disabled = true;
  lireFichiers($('c-pieces')).then(function(pieces){
    return api('POST', '/courrier/' + encodeURIComponent(boiteCourante) + '/envoyer', {a: $('c-a').value, cc: $('c-cc').value, sujet: $('c-sujet').value, texte: $('c-texte').value, pieces: pieces, en_reponse_a: compose.en_reponse_a, references: compose.references, transfert_de: compose.source});
  }).then(function(){ toast('Message envoyé.'); $('c-compose').classList.add('hidden'); if ($('c-dossier').value === 'envoyes') listerMessages(); }).catch(erreur).then(function(){ b.disabled = false; });
});

/* --- réglages -------------------------------------------------------- */
function chargerReglages(){
  api('GET', '/reglages').then(function(d){
    $('r-mailu-url').value = d.mailu_url || ''; $('r-hote').value = d.hote || ''; $('r-cert').value = d.nom_certificat || '';
    $('r-jeton-etat').textContent = d.mailu_jeton_defini ? 'jeton enregistré' : 'aucun jeton'; $('r-jeton-etat').className = 'pill' + (d.mailu_jeton_defini ? ' ok' : '');
    $('r-sauvegardes').querySelector('tbody').innerHTML = d.sauvegardes.map(function(s){ return '<tr><td class="mono">' + esc(s) + '</td><td><button data-restaurer="' + esc(s) + '">Restaurer</button></td></tr>'; }).join('') || '<tr><td class="aide">Aucune sauvegarde.</td></tr>';
    $('r-journal').textContent = d.journal.join('\n') || '(vide)';
  }).catch(erreur);
}
$('r-save').addEventListener('click', function(){ api('PUT', '/reglages', {mailu_url: $('r-mailu-url').value.trim(), mailu_jeton: $('r-mailu-jeton').value, hote: $('r-hote').value.trim(), nom_certificat: $('r-cert').value.trim()}).then(function(){ toast('Réglages enregistrés.'); $('r-mailu-jeton').value = ''; chargerReglages(); }).catch(erreur); });
$('r-tester').addEventListener('click', function(){ api('POST', '/reglages/tester-mailu', {}).then(function(d){ toast('API Mailu : domaine ' + d.domaine + ' reconnu.'); }).catch(erreur); });
$('r-mdp').addEventListener('click', function(){ api('POST', '/mot-de-passe', {ancien: $('r-ancien').value, nouveau: $('r-nouveau').value}).then(function(){ toast('Mot de passe changé.'); $('r-ancien').value = $('r-nouveau').value = ''; }).catch(erreur); });
$('r-sauvegardes').addEventListener('click', function(ev){ var b = ev.target.closest('button[data-restaurer]'); if (!b || !confirm('Restaurer ' + b.dataset.restaurer + ' ? Le contenu actuel est sauvegardé avant.')) return; api('POST', '/sauvegardes/restaurer', {nom: b.dataset.restaurer}).then(function(){ toast('Contenu restauré.'); chargerReglages(); }).catch(erreur); });

demarrer();
})();
</script>
</body>
</html>
"""
