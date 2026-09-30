console.info("%c METEOFRANCE-RADAR-CARD %c 0.2.0 ","background:#1f5fa8;color:#fff;border-radius:3px","");const t=globalThis,e=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),i=new WeakMap;let n=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const s=this.t;if(e&&void 0===t){const e=void 0!==s&&1===s.length;e&&(t=i.get(s)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),e&&i.set(s,t))}return t}toString(){return this.cssText}};const r=(t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new n(i,t,s)},o=e?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new n("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:a,defineProperty:l,getOwnPropertyDescriptor:h,getOwnPropertyNames:c,getOwnPropertySymbols:d,getPrototypeOf:p}=Object,u=globalThis,f=u.trustedTypes,m=f?f.emptyScript:"",g=u.reactiveElementPolyfillSupport,_=(t,e)=>t,b={toAttribute(t,e){switch(e){case Boolean:t=t?m:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},$=(t,e)=>!a(t,e),w={attribute:!0,type:String,converter:b,reflect:!1,useDefault:!1,hasChanged:$};Symbol.metadata??=Symbol("metadata"),u.litPropertyMetadata??=new WeakMap;let y=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=w){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&l(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:n}=h(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const r=i?.call(this);n?.call(this,e),this.requestUpdate(t,r,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??w}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const t=p(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const t=this.properties,e=[...c(t),...d(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(o(t))}else void 0!==t&&e.push(o(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const s=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((s,i)=>{if(e)s.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const e of i){const i=document.createElement("style"),n=t.litNonce;void 0!==n&&i.setAttribute("nonce",n),i.textContent=e.cssText,s.appendChild(i)}})(s,this.constructor.elementStyles),s}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const n=(void 0!==s.converter?.toAttribute?s.converter:b).toAttribute(e,s.type);this._$Em=t,null==n?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),n="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:b;this._$Em=i;const r=n.fromAttribute(e,t.type);this[i]=r??this._$Ej?.get(i)??r,this._$Em=null}}requestUpdate(t,e,s,i=!1,n){if(void 0!==t){const r=this.constructor;if(!1===i&&(n=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??$)(n,e)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:n},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==n||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};y.elementStyles=[],y.shadowRootOptions={mode:"open"},y[_("elementProperties")]=new Map,y[_("finalized")]=new Map,g?.({ReactiveElement:y}),(u.reactiveElementVersions??=[]).push("2.1.2");const v=globalThis,x=t=>t,A=v.trustedTypes,k=A?A.createPolicy("lit-html",{createHTML:t=>t}):void 0,C="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,S="?"+E,M=`<${S}>`,T=document,P=()=>T.createComment(""),I=t=>null===t||"object"!=typeof t&&"function"!=typeof t,U=Array.isArray,O="[ \t\n\f\r]",R=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,N=/-->/g,H=/>/g,D=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),q=/'/g,z=/"/g,B=/^(?:script|style|textarea|title)$/i,L=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),j=Symbol.for("lit-noChange"),F=Symbol.for("lit-nothing"),G=new WeakMap,W=T.createTreeWalker(T,129);function V(t,e){if(!U(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==k?k.createHTML(e):e}const Z=(t,e)=>{const s=t.length-1,i=[];let n,r=2===e?"<svg>":3===e?"<math>":"",o=R;for(let e=0;e<s;e++){const s=t[e];let a,l,h=-1,c=0;for(;c<s.length&&(o.lastIndex=c,l=o.exec(s),null!==l);)c=o.lastIndex,o===R?"!--"===l[1]?o=N:void 0!==l[1]?o=H:void 0!==l[2]?(B.test(l[2])&&(n=RegExp("</"+l[2],"g")),o=D):void 0!==l[3]&&(o=D):o===D?">"===l[0]?(o=n??R,h=-1):void 0===l[1]?h=-2:(h=o.lastIndex-l[2].length,a=l[1],o=void 0===l[3]?D:'"'===l[3]?z:q):o===z||o===q?o=D:o===N||o===H?o=R:(o=D,n=void 0);const d=o===D&&t[e+1].startsWith("/>")?" ":"";r+=o===R?s+M:h>=0?(i.push(a),s.slice(0,h)+C+s.slice(h)+E+d):s+E+(-2===h?e:d)}return[V(t,r+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class K{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let n=0,r=0;const o=t.length-1,a=this.parts,[l,h]=Z(t,e);if(this.el=K.createElement(l,s),W.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=W.nextNode())&&a.length<o;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(C)){const e=h[r++],s=i.getAttribute(t).split(E),o=/([.?@])?(.*)/.exec(e);a.push({type:1,index:n,name:o[2],strings:s,ctor:"."===o[1]?tt:"?"===o[1]?et:"@"===o[1]?st:Q}),i.removeAttribute(t)}else t.startsWith(E)&&(a.push({type:6,index:n}),i.removeAttribute(t));if(B.test(i.tagName)){const t=i.textContent.split(E),e=t.length-1;if(e>0){i.textContent=A?A.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],P()),W.nextNode(),a.push({type:2,index:++n});i.append(t[e],P())}}}else if(8===i.nodeType)if(i.data===S)a.push({type:2,index:n});else{let t=-1;for(;-1!==(t=i.data.indexOf(E,t+1));)a.push({type:7,index:n}),t+=E.length-1}n++}}static createElement(t,e){const s=T.createElement("template");return s.innerHTML=t,s}}function J(t,e,s=t,i){if(e===j)return e;let n=void 0!==i?s._$Co?.[i]:s._$Cl;const r=I(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),void 0===r?n=void 0:(n=new r(t),n._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=n:s._$Cl=n),void 0!==n&&(e=J(t,n._$AS(t,e.values),n,i)),e}class X{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??T).importNode(e,!0);W.currentNode=i;let n=W.nextNode(),r=0,o=0,a=s[0];for(;void 0!==a;){if(r===a.index){let e;2===a.type?e=new Y(n,n.nextSibling,this,t):1===a.type?e=new a.ctor(n,a.name,a.strings,this,t):6===a.type&&(e=new it(n,this,t)),this._$AV.push(e),a=s[++o]}r!==a?.index&&(n=W.nextNode(),r++)}return W.currentNode=T,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class Y{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=F,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=J(this,t,e),I(t)?t===F||null==t||""===t?(this._$AH!==F&&this._$AR(),this._$AH=F):t!==this._$AH&&t!==j&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>U(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==F&&I(this._$AH)?this._$AA.nextSibling.data=t:this.T(T.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=K.createElement(V(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new X(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=G.get(t.strings);return void 0===e&&G.set(t.strings,e=new K(t)),e}k(t){U(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const n of t)i===e.length?e.push(s=new Y(this.O(P()),this.O(P()),this,this.options)):s=e[i],s._$AI(n),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=x(t).nextSibling;x(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class Q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,n){this.type=1,this._$AH=F,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=F}_$AI(t,e=this,s,i){const n=this.strings;let r=!1;if(void 0===n)t=J(this,t,e,0),r=!I(t)||t!==this._$AH&&t!==j,r&&(this._$AH=t);else{const i=t;let o,a;for(t=n[0],o=0;o<n.length-1;o++)a=J(this,i[s+o],e,o),a===j&&(a=this._$AH[o]),r||=!I(a)||a!==this._$AH[o],a===F?t=F:t!==F&&(t+=(a??"")+n[o+1]),this._$AH[o]=a}r&&!i&&this.j(t)}j(t){t===F?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class tt extends Q{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===F?void 0:t}}class et extends Q{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==F)}}class st extends Q{constructor(t,e,s,i,n){super(t,e,s,i,n),this.type=5}_$AI(t,e=this){if((t=J(this,t,e,0)??F)===j)return;const s=this._$AH,i=t===F&&s!==F||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==F&&(s===F||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class it{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){J(this,t)}}const nt=v.litHtmlPolyfillSupport;nt?.(K,Y),(v.litHtmlVersions??=[]).push("3.3.3");const rt=globalThis;let ot=class extends y{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let n=i._$litPart$;if(void 0===n){const t=s?.renderBefore??null;i._$litPart$=n=new Y(e.insertBefore(P(),t),t,void 0,s??{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return j}};ot._$litElement$=!0,ot.finalized=!0,rt.litElementHydrateSupport?.({LitElement:ot});const at=rt.litElementPolyfillSupport;at?.({LitElement:ot}),(rt.litElementVersions??=[]).push("4.2.2");const lt=1,ht=2,ct=t=>(...e)=>({_$litDirective$:t,values:e});let dt=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};const pt=(t,e)=>{const s=t._$AN;if(void 0===s)return!1;for(const t of s)t._$AO?.(e,!1),pt(t,e);return!0},ut=t=>{let e,s;do{if(void 0===(e=t._$AM))break;s=e._$AN,s.delete(t),t=e}while(0===s?.size)},ft=t=>{for(let e;e=t._$AM;t=e){let s=e._$AN;if(void 0===s)e._$AN=s=new Set;else if(s.has(t))break;s.add(t),_t(e)}};function mt(t){void 0!==this._$AN?(ut(this),this._$AM=t,ft(this)):this._$AM=t}function gt(t,e=!1,s=0){const i=this._$AH,n=this._$AN;if(void 0!==n&&0!==n.size)if(e)if(Array.isArray(i))for(let t=s;t<i.length;t++)pt(i[t],!1),ut(i[t]);else null!=i&&(pt(i,!1),ut(i));else pt(this,t)}const _t=t=>{t.type==ht&&(t._$AP??=gt,t._$AQ??=mt)};class bt extends dt{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,s){super._$AT(t,e,s),ft(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(pt(this,t),ut(this))}setValue(t){if((t=>void 0===t.strings)(this._$Ct))this._$Ct._$AI(t,this);else{const e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}}class $t{}const wt=new WeakMap,yt=ct(class extends bt{render(t){return F}update(t,[e]){const s=e!==this.G;return s&&this.rt(void 0),(s||this.lt!==this.ct)&&(this.G=e,this.ht=t.options?.host,this.rt(this.ct=t.element)),F}rt(t){if(void 0!==this.G)if(this.isConnected||(t=void 0),"function"==typeof this.G){const e=this.ht??globalThis;let s=wt.get(e);void 0===s&&(s=new WeakMap,wt.set(e,s)),void 0!==s.get(this.G)&&this.G.call(this.ht,void 0),s.set(this.G,t),void 0!==t&&this.G.call(this.ht,t)}else this.G.value=t}get lt(){return"function"==typeof this.G?wt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});class vt extends Error{constructor(t,e){super(t),this.status=e,this.name="RadarApiError"}}class xt{constructor(t){this.hass=t}get client(){const t=this.hass();if(!t)throw new vt("Home Assistant is not connected",null);return t}frames(t){return this.client.callApi("GET",`meteofrance_radar/frames?period=${t}`)}async blob(t){const e=await this.client.fetchWithAuth(t);if(!e.ok)throw new vt(`${t}: HTTP ${e.status}`,e.status);return e.blob()}}function At(t){const e=Math.max(0,Math.round(t));if(e<60)return`+${e} min`;const s=Math.floor(e/60),i=e%60;return 0===i?`+${s} h`:`+${s} h ${String(i).padStart(2,"0")}`}const kt={credit:"Météo-France data",gap:t=>`gap of ${t} min skipped`,loading:"Loading the radar...",empty:"No radar image yet. The first one shows up a few minutes after setup.",error:"Could not load the radar images. Trying again in a minute.",play:"Play",pause:"Pause",stepBack:"Previous image",stepForward:"Next image",timeSlider:"Time",periods:{"3h":"3 h","24h":"24 h","7d":"7 d","30d":"30 d",all:"All"},periodGroup:"Period",pin:"Home",noData:"no data",legend:"Rain rate",forecast:"Forecast",forecastLead:t=>`Forecast ${At(t)}`,now:"Now",attribution:(t,e)=>`Radar: ${t} | Basemap: ${e}`,form:{default_period:"Default period",autoplay:"Play on load",show_legend:"Show the legend",show_forecast:"Continue with the forecast",frame_duration_ms:"Time on each image (ms)",crossfade_ms:"Crossfade (ms)",frameHelper:"From 100 to 5000 ms.",crossfadeHelper:"From 0 to 2000 ms, never longer than the time on each image."}},Ct={credit:"Données Météo-France",gap:t=>`saut de ${t} min`,loading:"Chargement du radar...",empty:"Pas encore d'image radar. La première arrive quelques minutes après l'installation.",error:"Impossible de charger les images radar. Nouvel essai dans une minute.",play:"Lecture",pause:"Pause",stepBack:"Image précédente",stepForward:"Image suivante",timeSlider:"Heure",periods:{"3h":"3 h","24h":"24 h","7d":"7 j","30d":"30 j",all:"Tout"},periodGroup:"Période",pin:"Maison",noData:"pas de données",legend:"Intensité de pluie",forecast:"Prévision",forecastLead:t=>`Prévision ${At(t)}`,now:"Maintenant",attribution:(t,e)=>`Radar : ${t} | Fond de carte : ${e}`,form:{default_period:"Période par défaut",autoplay:"Lecture automatique",show_legend:"Afficher la légende",show_forecast:"Continuer avec la prévision",frame_duration_ms:"Durée de chaque image (ms)",crossfade_ms:"Fondu enchaîné (ms)",frameHelper:"De 100 à 5000 ms.",crossfadeHelper:"De 0 à 2000 ms, jamais plus que la durée de chaque image."}};function Et(t){return t?.toLowerCase().startsWith("fr")?"fr":"en"}function St(t){return"fr"===Et(t)?Ct:kt}const Mt=new Map;function Tt(t,e,s){const i={};for(const s of function(t){const e=t??"",s=Mt.get(e);if(s)return s;const i={hourCycle:"h23",day:"2-digit",month:"2-digit",year:"2-digit",hour:"2-digit",minute:"2-digit"};let n;try{n=new Intl.DateTimeFormat("en-GB",{...i,timeZone:t})}catch{n=new Intl.DateTimeFormat("en-GB",i)}return Mt.set(e,n),n}(e).formatToParts(new Date(t)))i[s.type]=s.value;const n="fr"===Et(s)?"h":":";return`${i.day}/${i.month}/${i.year} ${i.hour}${n}${i.minute}`}const Pt={frames:[],nowIndex:-1,forecastCount:0};function It(t){const e=t.frames.length;return 0===t.forecastCount||t.nowIndex<0||e<2?null:t.nowIndex/(e-1)*100}const Ut="important",Ot=" !"+Ut,Rt=ct(class extends dt{constructor(t){if(super(t),t.type!==lt||"style"!==t.name||t.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(t){return Object.keys(t).reduce((e,s)=>{const i=t[s];return null==i?e:e+`${s=s.includes("-")?s:s.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${i};`},"")}update(t,[e]){const{style:s}=t.element;if(void 0===this.ft)return this.ft=new Set(Object.keys(e)),this.render(e);for(const t of this.ft)null==e[t]&&(this.ft.delete(t),t.includes("-")?s.removeProperty(t):s[t]=null);for(const t in e){const i=e[t];if(null!=i){this.ft.add(t);const e="string"==typeof i&&i.endsWith(Ot);t.includes("-")||e?s.setProperty(t,e?i.slice(0,-11):i,e?Ut:""):s[t]=i}}return j}});function Nt(t,e,s){return L`
    <div class="legend" role="list" aria-label=${e.legend}>
      <span class="legend-unit">${t.unit}</span>
      ${t.colors.map((e,i)=>L`
          <span class="legend-item" role="listitem">
            <span class="swatch" style="background:${e}"></span>
            <span class="legend-label">${function(t,e){const s=String(t);return"fr"===e?s.replace(".",","):s}(t.levels[i]??0,s)}</span>
          </span>
        `)}
      <span class="legend-item" role="listitem">
        <span class="swatch" style="background:${t.nodata_color}"></span>
        <span class="legend-label">${e.noData}</span>
      </span>
    </div>
  `}const Ht=["3h","24h","7d","30d","all"];function Dt(t){const e=t?.pin;return t&&e?.inside?{left:e.x/t.grid.width*100,top:e.y/t.grid.height*100}:null}function qt(t,e){const s=t.pin,i=s?{left:`${s.left}%`,top:`${s.top}%`}:{},n=String(t.aspect),r=t.fill?{"--map-aspect":n}:{"aspect-ratio":n},o=null!==t.leadMin;return L`
    <div class="stage ${o?"forecast":""}" style=${Rt(r)}>
      <div class="map">
        <canvas ${yt(e.canvasRef)}></canvas>
        <div
          class="pin"
          title=${t.strings.pin}
          ?hidden=${null===s}
          style=${Rt(i)}
        ></div>
        ${o?L`<div class="banner" role="note">${t.strings.forecast}</div>`:F}
      </div>
      ${function(t){const{strings:e}=t;return"loading"===t.state?L`<div class="message">${e.loading}</div>`:"empty"===t.state?L`<div class="message empty">${e.empty}</div>`:"error"===t.state?L`<div class="message error" role="alert">${e.error}</div>`:F}(t)}
    </div>
  `}function zt(t,e){const{strings:s}=t,i=0===t.count;return L`
    <div class="controls">
      <button
        class="icon play"
        ?disabled=${i}
        aria-label=${t.playing?s.pause:s.play}
        title=${t.playing?s.pause:s.play}
        @click=${e.togglePlay}
      >${t.playing?"⏸":"▶"}</button>
      <button
        class="icon back"
        ?disabled=${i}
        aria-label=${s.stepBack}
        title=${s.stepBack}
        @click=${()=>e.step(-1)}
      >⏮</button>
      <button
        class="icon forward"
        ?disabled=${i}
        aria-label=${s.stepForward}
        title=${s.stepForward}
        @click=${()=>e.step(1)}
      >⏭</button>
      ${function(t,e,s){const i=t.nowPct;return L`
    <div class="slider">
      <input
        type="range"
        min="0"
        max=${Math.max(0,t.count-1)}
        step="1"
        aria-label=${t.strings.timeSlider}
        ?disabled=${s}
        .value=${String(t.position)}
        @input=${t=>e.scrub(Number(t.target.value))}
        @change=${e.scrubEnd}
      />
      ${null!==i?L`<div class="marks">
              <div class="forecast-track" style=${Rt({left:`${i}%`})}></div>
              <div
                class="now-marker"
                title=${t.strings.now}
                style=${Rt({left:`${i}%`})}
              ></div>
            </div>`:F}
    </div>
  `}(t,e,i)}
    </div>
  `}function Bt(t,e){const s=t.attribution;return L`
    <ha-card class=${t.fill?"fill":""}>
      ${function(t){const{strings:e}=t;return L`
    <div class="title">
      ${t.time?L`<span class="time">${t.time}</span>`:F}
      ${null!==t.leadMin?L`<span class="badge">${e.forecastLead(t.leadMin)}</span>`:F}
      <span class="credit">${e.credit}</span>
      ${t.gapMin>0?L`<span class="gap" role="note">${e.gap(t.gapMin)}</span>`:F}
    </div>
  `}(t)} ${qt(t,e)} ${zt(t,e)}
      ${function(t,e){return L`
    <div class="periods" role="group" aria-label=${t.strings.periodGroup}>
      ${Ht.map(s=>L`
          <button
            class="chip"
            data-period=${s}
            aria-pressed=${t.period===s?"true":"false"}
            @click=${()=>e.selectPeriod(s)}
          >${t.strings.periods[s]}</button>
        `)}
    </div>
  `}(t,e)}
      ${t.legend?Nt(t.legend,t.strings,t.language):F}
      ${s?L`<div class="attribution">
              ${t.strings.attribution(s.radar,s.basemap)}
            </div>`:F}
    </ha-card>
  `}const Lt={columns:12,rows:"auto",min_columns:6,min_rows:4};function jt(t){return t?.locale?.language??t?.language}class Ft{constructor(){this.url=null,this.bitmap=null}async load(t,e,s){if(t===this.url)return!1;try{const i=await s(await e(t));return this.bitmap?.close(),this.bitmap=i,this.url=t,!0}catch(t){return console.warn("meteofrance-radar-card: basemap failed",t),!1}}}class Gt{constructor(t,e,s,i){this.canvas=t,this.width=e,this.height=s,this.contextOf=i,this.basemap=null,t.width=e,t.height=s,this.context=i(t),this.slots=[this.makeSlot(),this.makeSlot()]}matches(t,e,s){return this.canvas===t&&this.width===e&&this.height===s}setBasemap(t){this.basemap=t,this.reset()}reset(){for(const t of this.slots)t.key=null}drawBasemap(){const t=this.context;t&&(t.globalAlpha=1,t.clearRect(0,0,this.width,this.height),this.basemap&&t.drawImage(this.basemap,0,0,this.width,this.height))}draw(t,e,s){const i=this.context;if(!i)return;const n=this.composite(t,e?.key??null);if(i.globalAlpha=1,i.clearRect(0,0,this.width,this.height),i.drawImage(n,0,0),null===e||s<=0)return;const r=this.composite(e,t.key);i.globalAlpha=Math.min(1,s),i.drawImage(r,0,0),i.globalAlpha=1}makeSlot(){const t=document.createElement("canvas");return t.width=this.width,t.height=this.height,{key:null,canvas:t}}composite(t,e){const s=this.slots.find(e=>e.key===t.key);if(s)return s.canvas;const i=this.slots.find(t=>t.key!==e)??this.slots[0],n=this.contextOf(i.canvas);return n&&(n.globalAlpha=1,n.clearRect(0,0,this.width,this.height),this.basemap&&n.drawImage(this.basemap,0,0,this.width,this.height),n.drawImage(t.bitmap,0,0,this.width,this.height)),i.key=t.key,i.canvas}}const Wt={default_period:"3h",autoplay:!0,show_legend:!0,show_forecast:!0,frame_duration_ms:500,crossfade_ms:300},Vt=["type","grid_options","layout_options","view_layout","visibility"],Zt=new Set([...Vt,...Object.keys(Wt)]);class Kt extends Error{constructor(t){super(t),this.name="CardConfigError"}}function Jt(t,e){const s=t[e];if(void 0===s)return Wt[e];if("boolean"!=typeof s)throw new Kt(`${e} must be true or false`);return s}function Xt(t,e,s,i){const n=t[e];if(void 0===n)return Wt[e];if("number"!=typeof n||!Number.isFinite(n)||n<s||n>i)throw new Kt(`${e} must be a number from ${s} to ${i}`);return Math.round(n)}function Yt(){const t=document.querySelector("home-assistant");return t?.hass?.locale?.language??t?.hass?.language??navigator.language}const Qt="meteofrance-radar-card-editor";customElements.get(Qt)||customElements.define(Qt,class extends ot{set hass(t){const e=this._hass?.locale?.language??this._hass?.language;this._hass=t,e!==(t.locale?.language??t.language)&&this.requestUpdate()}get hass(){return this._hass}setConfig(t){this._config=t,this.requestUpdate()}render(){const t=this._config;if(!t)return L``;const e=function(t){const e=St(t),s=e.form,i=[{name:"default_period",selector:{select:{mode:"dropdown",options:Ht.map(t=>({value:t,label:e.periods[t]}))}}},{name:"autoplay",selector:{boolean:{}}},{name:"show_legend",selector:{boolean:{}}},{name:"show_forecast",selector:{boolean:{}}},{name:"frame_duration_ms",selector:{number:{min:100,max:5e3,step:100,mode:"box",unit_of_measurement:"ms"}}},{name:"crossfade_ms",selector:{number:{min:0,max:2e3,step:50,mode:"box",unit_of_measurement:"ms"}}}],n={default_period:s.default_period,autoplay:s.autoplay,show_legend:s.show_legend,show_forecast:s.show_forecast,frame_duration_ms:s.frame_duration_ms,crossfade_ms:s.crossfade_ms},r={frame_duration_ms:s.frameHelper,crossfade_ms:s.crossfadeHelper};return{schema:i,computeLabel:t=>n[t.name],computeHelper:t=>r[t.name]}}(this._hass?.locale?.language??this._hass?.language??Yt());return L`
      <ha-form
        .hass=${this._hass}
        .data=${function(t){return{...Wt,...t}}(t)}
        .schema=${e.schema}
        .computeLabel=${e.computeLabel}
        .computeHelper=${e.computeHelper}
        @value-changed=${t=>this._changed(t)}
      ></ha-form>
    `}_changed(t){if(t.stopPropagation(),!this._config)return;const e=function(t,e){const s={type:t.type};for(const e of Vt)"type"!==e&&void 0!==t[e]&&(s[e]=t[e]);for(const t of Object.keys(Wt)){const i=e[t];null!=i&&""!==i&&i!==Wt[t]&&(s[t]=i)}return s}(this._config,t.detail.value);this._config=e,this.dispatchEvent(new CustomEvent("config-changed",{detail:{config:e},bubbles:!0,composed:!0}))}});const te="ha-form";function ee(t,e,s,i){const n=[];for(let r=s;r<=i&&r<t.length;r+=1){const s=t[(e+r)%t.length];void 0!==s&&n.push(s)}return n}class se{constructor(t){this.deps=t,this.blobs=new Map,this.pending=new Map,this.queue=[],this.active=0,this.bitmaps=new Map,this.decoding=new Map,this.wanted=new Set,this.windowKey="",this.closed=!1,this.failed=new Map}blob(t,e=!0){const s=this.blobs.get(t);if(s)return this.blobs.delete(t),this.blobs.set(t,s),Promise.resolve(s);const i=this.failed.get(t);if(i&&Date.now()-i.at<3e5)return Promise.reject(i.error);this.failed.delete(t);const n=this.pending.get(t);if(n)return e&&this.promote(t),n;const r=new Promise((s,i)=>{const n={url:t,resolve:s,reject:i};e?this.queue.unshift(n):this.queue.push(n)});return this.pending.set(t,r),this.pump(),r}prefetch(t){for(const e of t)this.blob(e,!1).catch(()=>{})}setWindow(t){this.wanted=new Set(t);for(const[t,e]of this.bitmaps)this.wanted.has(t)||(e.close(),this.bitmaps.delete(t));for(const e of t)this.decode(e).catch(()=>{})}focus(t,e){const s=ee(t,e,0,3),i=s.join("|");i!==this.windowKey&&(this.windowKey=i,this.setWindow(s),this.prefetch(ee(t,e,4,11)))}async ensure(t){await Promise.all(t.map(t=>this.decode(t)))}bitmap(t){return this.bitmaps.get(t)??null}close(){this.closed=!0;for(const t of this.queue)t.reject(new Error("loader closed"));this.queue.length=0;for(const t of this.bitmaps.values())t.close();this.bitmaps.clear()}decode(t){const e=this.bitmaps.get(t);if(e)return Promise.resolve(e);const s=this.decoding.get(t);if(s)return s;const i=this.blob(t).then(t=>this.deps.decode(t)).then(e=>(this.closed||!this.wanted.has(t)?e.close():this.bitmaps.set(t,e),e)).finally(()=>this.decoding.delete(t));return this.decoding.set(t,i),i}promote(t){const e=this.queue.findIndex(e=>e.url===t);if(e<=0)return;const[s]=this.queue.splice(e,1);s&&this.queue.unshift(s)}pump(){for(;!this.closed&&this.active<4;){const t=this.queue.shift();if(!t)return;this.active+=1,this.deps.fetchBlob(t.url).then(e=>{this.remember(t.url,e),t.resolve(e)},e=>{this.failed.set(t.url,{at:Date.now(),error:e}),t.reject(e)}).finally(()=>{this.pending.delete(t.url),this.active-=1,this.pump()})}}remember(t,e){this.blobs.set(t,e);for(const t of this.blobs.keys()){if(this.blobs.size<=300)return;this.blobs.delete(t)}}}function ie(t,e,s){return s<=0?0:((t+e)%s+s)%s}function ne(t,e,s){const i=t[s],n=i?e[i.frame]:void 0;return i&&void 0!==n?[n,null===i.next?null:e[i.next]??null]:null}class re{constructor(t,e){this.hooks=t,this.clock=e,this.stepIndex=0,this.playing=!1,this.waiting=!1,this.elapsed=0,this.resumeAfterScrub=!1,this.lastTick=null,this.handle=null}play(){this.playing||0===this.hooks.steps().length||(this.playing=!0,this.lastTick=null,this.schedule(),this.hooks.changed())}pause(){null!==this.handle&&this.clock.cancelFrame(this.handle),this.handle=null,this.playing&&(this.playing=!1,this.hooks.changed())}toggle(){this.playing?this.pause():this.play()}moveTo(t){this.stepIndex=t,this.elapsed=0,this.lastTick=null}async seek(t){this.moveTo(t),this.hooks.changed(),this.hooks.render(t,0)||(await this.hooks.ensure(t),this.stepIndex===t&&0===this.elapsed&&this.hooks.render(t,0))}stepBy(t){return this.pause(),this.seek(ie(this.stepIndex,t,this.hooks.steps().length))}scrub(t){return this.playing&&(this.resumeAfterScrub=!0,this.pause()),this.seek(t)}scrubEnd(){this.resumeAfterScrub&&this.play(),this.resumeAfterScrub=!1}schedule(){this.handle=this.clock.requestFrame(()=>this.tick())}tick(){if(this.handle=null,!this.playing||0===this.hooks.steps().length)return;const t=this.clock.now(),e=null===this.lastTick?0:t-this.lastTick;this.lastTick=t,this.waiting||this.advance(e),this.schedule()}advance(t){const e=this.hooks.steps(),s=this.stepIndex;this.stepIndex=Math.min(this.stepIndex,e.length-1),this.elapsed+=t;let i=e[this.stepIndex];for(;i&&this.elapsed>=i.durationMs;)this.elapsed-=i.durationMs,this.stepIndex=ie(this.stepIndex,1,e.length),i=e[this.stepIndex];i&&(this.stepIndex!==s&&this.hooks.changed(),this.hooks.render(this.stepIndex,function(t,e){if(null===t.next||t.fadeMs<=0)return 0;const s=t.durationMs-t.fadeMs;return e<=s?0:Math.min(1,(e-s)/t.fadeMs)}(i,this.elapsed))||this.wait(this.stepIndex))}wait(t){this.waiting=!0,this.hooks.changed(),this.hooks.ensure(t).catch(()=>{this.stepIndex===t&&this.moveTo(ie(t,1,this.hooks.steps().length))}).finally(()=>{this.waiting=!1,this.lastTick=null,this.hooks.changed()})}}const oe=r`
  :host {
    display: block;
    height: 100%;
  }
  ha-card {
    overflow: hidden;
    padding-bottom: 8px;
    box-sizing: border-box;
  }
  ha-card.fill {
    height: 100%;
    display: flex;
    flex-direction: column;
  }
  ha-card.fill > * {
    flex: none;
  }
  .title {
    display: flex;
    flex-wrap: wrap;
    align-items: baseline;
    gap: 4px 10px;
    padding: 12px 16px 8px;
    font-size: 1.1rem;
    color: var(--primary-text-color);
  }
  .time {
    font-weight: 500;
    font-variant-numeric: tabular-nums;
  }
  .credit {
    font-size: 0.85rem;
    color: var(--secondary-text-color);
  }
  .badge {
    font-size: 0.8rem;
    font-weight: 500;
    padding: 1px 8px;
    border-radius: 10px;
    border: 1px dashed var(--primary-color, #03a9f4);
    color: var(--primary-color, #03a9f4);
  }
  .gap {
    font-size: 0.8rem;
    padding: 1px 8px;
    border-radius: 10px;
    background: var(--warning-color, #ffa600);
    color: var(--text-primary-color, #fff);
  }
  .stage {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: #eef0f2;
  }
  .map {
    position: relative;
    width: 100%;
    height: 100%;
  }
  ha-card.fill .stage {
    flex: 1 1 auto;
    min-height: 0;
    aspect-ratio: auto;
    container-type: size;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  ha-card.fill .map {
    width: min(100cqw, calc(100cqh * var(--map-aspect, 16 / 9)));
    height: auto;
    aspect-ratio: var(--map-aspect, 16 / 9);
  }
  .stage.forecast .map {
    outline: 2px dashed var(--primary-color, #03a9f4);
    outline-offset: -2px;
  }
  .banner {
    position: absolute;
    top: 8px;
    left: 8px;
    padding: 2px 10px;
    border-radius: 12px;
    font-size: 0.8rem;
    font-weight: 500;
    background: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
    pointer-events: none;
  }
  canvas {
    display: block;
    width: 100%;
    height: 100%;
  }
  .pin {
    position: absolute;
    width: 14px;
    height: 14px;
    margin: -7px 0 0 -7px;
    border-radius: 50%;
    background: var(--accent-color, #ff5722);
    border: 2px solid #fff;
    box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.45);
    box-sizing: border-box;
    pointer-events: none;
  }
  .pin[hidden] {
    display: none;
  }
  .message {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    text-align: center;
    background: rgba(255, 255, 255, 0.72);
    color: #333;
  }
  .message.error {
    color: var(--error-color, #db4437);
  }
  .controls {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
    padding: 8px 12px 0;
  }
  .controls button {
    flex: none;
  }
  .slider {
    position: relative;
    flex: 1 1 140px;
    min-width: 0;
    display: flex;
    align-items: center;
  }
  .slider input[type="range"] {
    width: 100%;
    min-width: 0;
    margin: 0;
  }
  /* Inset by half a thumb, so a percentage lines up with the thumb centre. */
  .marks {
    position: absolute;
    top: 0;
    bottom: 0;
    left: 8px;
    right: 8px;
    pointer-events: none;
  }
  .forecast-track {
    position: absolute;
    top: 50%;
    right: 0;
    height: 6px;
    transform: translateY(-50%);
    border-radius: 3px;
    background: var(--primary-color, #03a9f4);
    opacity: 0.25;
  }
  .now-marker {
    position: absolute;
    top: 15%;
    bottom: 15%;
    width: 2px;
    margin-left: -1px;
    background: var(--primary-text-color, #212121);
  }
  button {
    font: inherit;
    cursor: pointer;
    border: none;
    background: none;
    color: var(--primary-text-color);
    border-radius: 6px;
    padding: 4px 8px;
  }
  button:disabled {
    cursor: default;
    opacity: 0.4;
  }
  button.icon {
    font-size: 1.1rem;
    min-width: 36px;
  }
  .periods {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    padding: 8px 16px 0;
  }
  .chip {
    font-size: 0.85rem;
    border: 1px solid var(--divider-color, #ccc);
    border-radius: 14px;
    padding: 2px 12px;
  }
  .chip[aria-pressed="true"] {
    background: var(--primary-color, #03a9f4);
    border-color: var(--primary-color, #03a9f4);
    color: var(--text-primary-color, #fff);
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    padding: 10px 16px 0;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }
  .legend-unit {
    font-weight: 500;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
    border: 1px solid rgba(0, 0, 0, 0.15);
  }
  .attribution {
    padding: 8px 16px 0;
    font-size: 0.7rem;
    color: var(--secondary-text-color);
  }
`;class ae extends ot{constructor(){super(...arguments),this.seams=function(){const t="function"==typeof requestAnimationFrame;return{createImageBitmap:t=>createImageBitmap(t),context2d:t=>t.getContext("2d"),now:()=>performance.now(),requestFrame:e=>t?requestAnimationFrame(()=>e()):window.setTimeout(e,16),cancelFrame:e=>t?cancelAnimationFrame(e):clearTimeout(e)}}(),this._period=Wt.default_period,this._data=null,this._playlist=Pt,this._fill=!1,this._state="loading",this._steps=[],this._shown=0,this._generation=0,this._refreshTimer=null,this._resumeOnConnect=!1,this._basemap=new Ft,this._compositor=null,this._canvasRef=new $t,this._api=new xt(()=>this._hass),this._loader=new se({fetchBlob:t=>this._api.blob(t),decode:t=>this.seams.createImageBitmap(t)}),this._playback=new re({steps:()=>this._steps,render:(t,e)=>this._render(t,e),ensure:t=>this._ensure(t),changed:()=>this.requestUpdate()},{now:()=>this.seams.now(),requestFrame:t=>this.seams.requestFrame(t),cancelFrame:t=>this.seams.cancelFrame(t)})}static async getConfigElement(){return await async function(t=customElements,e=5e3){if(t.get(te))return;const s=t.get("hui-tile-card");try{await(s?.getConfigElement?.())}catch(t){console.warn("meteofrance-radar-card: could not preload the form editor",t)}let i;const n=new Promise(t=>{i=setTimeout(t,e)});await Promise.race([t.whenDefined(te).then(()=>{}),n]),clearTimeout(i)}(),document.createElement(Qt)}static getStubConfig(){return{default_period:Wt.default_period,autoplay:Wt.autoplay}}setConfig(t){const e=function(t){if(null===t||"object"!=typeof t)throw new Kt("the card config must be an object");for(const e of Object.keys(t))if(!Zt.has(e))throw new Kt(`unknown option: ${e}`);const e=t.default_period??Wt.default_period;if(!Ht.includes(e))throw new Kt(`default_period must be one of ${Ht.join(", ")}`);const s=Xt(t,"frame_duration_ms",100,5e3),i=Xt(t,"crossfade_ms",0,2e3);return{default_period:e,autoplay:Jt(t,"autoplay"),show_legend:Jt(t,"show_legend"),show_forecast:Jt(t,"show_forecast"),frame_duration_ms:s,crossfade_ms:Math.min(i,s)}}(t),s=this._config?.default_period!==e.default_period;this._config=e,this._fill=function(t){const e=t.grid_options;return"number"==typeof e?.rows}(t),this._rebuild(),s&&(this._period=e.default_period,this.isConnected&&this._load()),this.requestUpdate()}set hass(t){const e=this._hass;this._hass=t,e||!this.isConnected||this._data||this._load(),jt(e)===jt(t)&&e?.config.time_zone===t.config.time_zone||this.requestUpdate()}get hass(){return this._hass}getCardSize(){return 7}getGridOptions(){return{...Lt}}connectedCallback(){super.connectedCallback(),this._refreshTimer=window.setInterval(()=>{this._refresh()},6e4),this._resumeOnConnect&&this._playback.play(),this._data?this._refresh():this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._refreshTimer&&window.clearInterval(this._refreshTimer),this._refreshTimer=null,this._resumeOnConnect=this._playback.playing,this._playback.pause()}updated(){const t=this._canvasRef.value;if(!t)return;const e=this._data?.grid.width??1920,s=this._data?.grid.height??1080;this._compositor?.matches(t,e,s)||(this._compositor=new Gt(t,e,s,this.seams.context2d),this._compositor.setBasemap(this._basemap.bitmap),this._compositor.drawBasemap())}render(){if(!this._config)return L``;return Bt(function(t){const{data:e,hass:s}=t,i=Et(jt(s)),n="ready"===t.state,r=n?t.playlist.frames[t.shown]:void 0;return{strings:St(i),language:i,state:t.state,time:r?Tt(r.time,s?.config.time_zone,i):null,gapMin:r?.gap_before_min??0,leadMin:r?.forecast?r.lead_min??0:null,nowPct:n?It(t.playlist):null,fill:t.fill,playing:t.playing,waiting:t.waiting,position:t.position,count:n?t.stepCount:0,period:t.period,pin:Dt(e),aspect:(e?.grid.width??1920)/(e?.grid.height??1080),legend:t.config.show_legend?e?.legend??null:null,attribution:e?.attribution??null}}({config:this._config,hass:this._hass,data:this._data,playlist:this._playlist,state:this._state,shown:this._shown,playing:this._playback.playing,waiting:this._playback.waiting,position:this._playback.stepIndex,stepCount:this._steps.length,period:this._period,fill:this._fill}),{canvasRef:this._canvasRef,togglePlay:()=>this._playback.toggle(),step:t=>{this._playback.stepBy(t).catch(le)},scrub:t=>{this._shown=t,this._playback.scrub(t).catch(le)},scrubEnd:()=>this._playback.scrubEnd(),selectPeriod:t=>this._selectPeriod(t)})}_rebuild(){const t=this._config??Wt;this._playlist=function(t,e){if(!t)return Pt;const s=t.frames.map(t=>({time:t.time,url:t.url,gap_before_min:t.gap_before_min,forecast:!1,lead_min:null})),i=s[s.length-1],n=i?Date.parse(i.time):Number.NEGATIVE_INFINITY,r=e?(t.forecast?.frames??[]).filter(t=>Date.parse(t.time)>n).map(t=>({time:t.time,url:t.url,gap_before_min:0,forecast:!0,lead_min:t.lead_min})):[];return{frames:[...s,...r],nowIndex:s.length-1,forecastCount:r.length}}(this._data,t.show_forecast),this._steps=function(t,e){const s=Math.max(1,e.frameMs),i=Math.max(0,Math.min(e.crossfadeMs,s));return t.map((e,n)=>{const r=t[n+1],o=void 0!==r&&r.gap_before_min<=0&&i>0;return{frame:n,next:o?n+1:null,durationMs:s,fadeMs:o?i:0}})}(this._playlist.frames,{frameMs:t.frame_duration_ms,crossfadeMs:t.crossfade_ms});const e=this._playlist.frames.length-1;this._shown>e&&(this._shown=Math.max(0,e)),this._playback.stepIndex>e&&this._playback.moveTo(Math.max(0,e))}_refresh(){const t="ready"===this._state?this._playlist.frames[this._shown]?.time:void 0;return this._load(t??null,!0)}async _load(t=null,e=!1){if(!this._hass||!this._config)return;const s=++this._generation;e||(this._playback.pause(),this._state="loading",this.requestUpdate());try{const e=await this._api.frames(this._period);if(s!==this._generation)return;const i=t=>this._api.blob(t),n=t=>this.seams.createImageBitmap(t);if(await this._basemap.load(e.basemap,i,n)&&this._compositor?.setBasemap(this._basemap.bitmap),s!==this._generation)return;await this._install(e,t)}catch(t){if(s!==this._generation)return;console.warn("meteofrance-radar-card: frame list request failed",t),e&&this._data||(this._state="error",this.requestUpdate())}}async _install(t,e){this._data=t,this._rebuild(),this._compositor?.reset();const s=this._playlist.frames;if(0===s.length)return this._playback.pause(),this._state="empty",this.requestUpdate(),await this.updateComplete,void this._compositor?.drawBasemap();this._state="ready";const i=null===e&&(this._config?.autoplay??Wt.autoplay),n=s.map(t=>t.time),r=null!==e?function(t,e){const s=Date.parse(e);let i=0;for(let e=0;e<t.length&&!(Date.parse(t[e]??"")>s);e+=1)i=e;return i}(n,e):null,o=function(t,e,s){return null!==e?e:s?0:Math.max(0,t.nowIndex)}(this._playlist,r,i);this._shown=o,this._playback.playing&&o===this._playback.stepIndex||this._playback.moveTo(o),this.requestUpdate(),await this.updateComplete,this._playback.playing||(await this._playback.seek(o).catch(le),i&&this._playback.play())}_urls(){return this._playlist.frames.map(t=>t.url)}_render(t,e){const s=ne(this._steps,this._urls(),t),i=this._compositor;if(!s||!i)return!1;this._loader.focus(this._urls(),t);const[n,r]=s,o=this._loader.bitmap(n),a=null===r?null:this._loader.bitmap(r);if(!o||null!==r&&!a)return!1;const l=null!==r&&a?{key:r,bitmap:a}:null;i.draw({key:n,bitmap:o},l,e);const h=this._steps[t],c=h?function(t,e){return null!==t.next&&e>=.5?t.next:t.frame}(h,e):t;return c!==this._shown&&(this._shown=c,this.requestUpdate()),!0}_ensure(t){const e=ne(this._steps,this._urls(),t);return e?(this._loader.focus(this._urls(),t),this._shown=t,this._loader.ensure(e.filter(t=>null!==t))):Promise.resolve()}_selectPeriod(t){t!==this._period&&(this._period=t,this._load())}}function le(t){console.warn("meteofrance-radar-card: layer failed",t)}ae.styles=oe;const he="meteofrance-rain-bar-card",ce={title:null,show_legend:!1},de=new Set(["type","grid_options","layout_options","view_layout","visibility","title","show_legend"]);class pe extends Error{constructor(t){super(t),this.name="RainBarConfigError"}}function ue(t){if(null===t||"object"!=typeof t)throw new pe("the card config must be an object");for(const e of Object.keys(t))if(!de.has(e))throw new pe(`unknown option: ${e}`);const{title:e,show_legend:s}=t;if(void 0!==e&&"string"!=typeof e)throw new pe("title must be text");if(void 0!==s&&"boolean"!=typeof s)throw new pe("show_legend must be true or false");return{title:e?.trim()?e:ce.title,show_legend:s??ce.show_legend}}const fe={loading:"Loading the rain forecast...",error:"Could not load the rain at home. Trying again in a few minutes.",notLocated:"Set your home location in the Home Assistant settings.",now:"Now",noData:"no data",bar:"Rain at home, past 3 hours and forecast",credit:t=>`Source: ${t}`,form:{title:"Title",show_legend:"Show the legend"}},me={loading:"Chargement de la prévision de pluie...",error:"Impossible de charger la pluie à la maison. Nouvel essai dans quelques minutes.",notLocated:"Indiquez l'emplacement de votre maison dans les paramètres de Home Assistant.",now:"Maintenant",noData:"pas de données",bar:"Pluie à la maison, 3 dernières heures et prévision",credit:t=>`Source : ${t}`,form:{title:"Titre",show_legend:"Afficher la légende"}};function ge(t){return"fr"===t?me:fe}const _e=9e5,be=[1,2,3,6];function $e(t,e,s){return s<=e?0:Math.min(100,Math.max(0,(t-e)/(s-e)*100))}const we=new Map;function ye(t,e){let s=0,i=0;for(const n of function(t){const e=t??"";let s=we.get(e);if(!s){const i={hour:"2-digit",minute:"2-digit",hourCycle:"h23"};try{s=new Intl.DateTimeFormat("en-GB",{...i,timeZone:t})}catch{s=new Intl.DateTimeFormat("en-GB",i)}we.set(e,s)}return s}(e).formatToParts(new Date(t)))"hour"===n.type&&(s=Number(n.value)%24),"minute"===n.type&&(i=Number(n.value));return[s,i]}function ve(t,e,s){const[i,n]=ye(t,e),r=String(i).padStart(2,"0"),o=String(n).padStart(2,"0");return"fr"===s?`${r}h${o}`:`${r}:${o}`}function xe(t,e){const s=String(t).padStart(2,"0");return"fr"===e?`${s}h`:`${s}:00`}function Ae(t,e,s,i,n,r){return`${`${ve(t,i,n)}-${ve(e,i,n)}`} · ${null===s?r:function(t,e){const s=String(Math.round(100*t)/100);return`${"fr"===e?s.replace(".",","):s} mm/h`}(s,n)}`}function ke(t,e,s,i,n=8){if(e-t<9e5)return[];const r=function(t,e,s){const i=[];for(let n=Math.ceil(t/_e)*_e;n<=e;n+=_e){const[t,e]=ye(n,s);0===e&&i.push([n,t])}return i}(t,e,s),o=function(t,e){for(const s of be)if(t.filter(t=>t%s===0).length<=e)return s;return be[be.length-1]??6}(r.map(([,t])=>t),n);return r.filter(([,t])=>t%o===0).map(([s,n])=>({time:s,percent:$e(s,t,e),label:xe(n,i)}))}const Ce=r`
  :host {
    display: block;
  }
  ha-card {
    padding: 12px 16px 10px;
    box-sizing: border-box;
    height: 100%;
  }
  .title {
    margin: 0 0 8px;
    font-size: 1rem;
    font-weight: 500;
    color: var(--primary-text-color);
  }
  .bar {
    position: relative;
    height: 28px;
    border-radius: 6px;
    overflow: hidden;
    background: var(--secondary-background-color, #e5e5e5);
  }
  .segment {
    position: absolute;
    top: 0;
    bottom: 0;
  }
  .segment.nodata {
    opacity: 0.35;
  }
  .segment.forecast {
    background-image: repeating-linear-gradient(
      45deg,
      rgba(255, 255, 255, 0.35) 0 2px,
      transparent 2px 6px
    );
  }
  /* White stripes vanish on a light track, so dry forecast stripes are grey. */
  .segment.forecast.dry {
    background-image: repeating-linear-gradient(
      45deg,
      rgba(128, 128, 128, 0.3) 0 2px,
      transparent 2px 6px
    );
  }
  .now {
    position: absolute;
    top: 0;
    bottom: 0;
    width: 2px;
    margin-left: -1px;
    background: var(--primary-text-color, #212121);
  }
  .ticks {
    position: relative;
    height: 1.2em;
    margin-top: 3px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }
  .tick {
    position: absolute;
    top: 0;
    transform: translateX(-50%);
    white-space: nowrap;
  }
  .tick.first {
    transform: none;
  }
  .tick.last {
    transform: translateX(-100%);
  }
  .message {
    padding: 4px 0;
    color: var(--secondary-text-color);
  }
  .message.error {
    color: var(--error-color, #db4437);
  }
  .credit {
    margin-top: 4px;
    font-size: 0.7rem;
    color: var(--secondary-text-color);
    text-align: right;
  }
  .legend {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 8px;
    padding-top: 6px;
    font-size: 0.75rem;
    color: var(--secondary-text-color);
  }
  .legend-unit {
    font-weight: 500;
  }
  .legend-item {
    display: inline-flex;
    align-items: center;
    gap: 3px;
  }
  .swatch {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }
`;function Ee(t,e,s,i,n){const r=Date.parse(t.start),o=Date.parse(t.end),a=function(t,e,s,i){const n=$e(t,s,i);return{left:n,width:Math.max(0,$e(e,s,i)-n)}}(r,o,e,s),l=function(t,e){return 11===t?e.nodata_color:t>=1&&t<=e.colors.length?e.colors[t-1]??null:null}(t.class,n),h=["segment","radar"===t.source?"observed":"forecast",11===t.class?"nodata":"",0===t.class?"dry":""].filter(Boolean).join(" "),c=`left:${a.left}%;width:${a.width}%${l?`;background-color:${l}`:""}`,d=Ae(r,o,t.mm_h,i.timeZone,i.language,i.strings.noData);return L`<div
    class=${h}
    style=${c}
    data-source=${t.source}
    data-class=${t.class}
    role="img"
    title=${d}
    aria-label=${d}
  ></div>`}function Se(t,e){const s=Date.parse(t.window.start),i=Date.parse(t.window.end),n=e.now>=s&&e.now<=i;return L`
    <div class="bar" role="group" aria-label=${e.strings.bar}>
      ${t.segments.map(n=>Ee(n,s,i,e,t.legend))}
      ${n?L`<div
              class="now"
              style="left:${$e(e.now,s,i)}%"
              title=${e.strings.now}
              aria-label=${e.strings.now}
            ></div>`:F}
    </div>
    ${function(t,e,s){const i=ke(t,e,s.timeZone,s.language,s.maxLabels);return L`<div class="ticks" aria-hidden="true">
    ${i.map(t=>{const e=t.percent<4?"first":t.percent>96?"last":"";return L`<span class="tick ${e}" style="left:${t.percent}%">${t.label}</span>`})}
  </div>`}(s,i,e)}
    ${e.showLegend?Nt(t.legend,St(e.language),e.language):F}
    <div class="credit">${e.strings.credit(t.attribution)}</div>
  `}function Me(t){return L`
    <ha-card>
      ${t.title?L`<h2 class="title">${t.title}</h2>`:F}
      ${function(t){const{data:e,strings:s}=t;return null===e?"error"===t.state?L`<div class="message error" role="alert">${s.error}</div>`:L`<div class="message loading">${s.loading}</div>`:e.located?Se(e,t):L`<div class="message located">${s.notLocated}</div>`}(t)}
    </ha-card>
  `}class Te extends ot{constructor(){super(...arguments),this._config=ce,this._data=null,this._state="loading",this._now=Date.now(),this._width=0,this._refreshTimer=null,this._nowTimer=null,this._resizeObserver=null,this._generation=0}static getConfigForm(){return function(t){const e=ge(Et(t)).form;return{schema:[{name:"title",selector:{text:{}}},{name:"show_legend",selector:{boolean:{}}}],computeLabel:t=>e[t.name],assertConfig:t=>{ue(t)}}}(Yt())}static getStubConfig(){return{}}setConfig(t){this._config=ue(t),this.requestUpdate()}set hass(t){const e=void 0===this._hass;this._hass=t,e&&this.isConnected&&this._load(),this.requestUpdate()}get hass(){return this._hass}getCardSize(){return 2}getGridOptions(){return{columns:12,rows:"auto",min_columns:3,min_rows:1}}connectedCallback(){super.connectedCallback(),this._now=Date.now(),this._refreshTimer=window.setInterval(()=>{this._load()},3e5),this._nowTimer=window.setInterval(()=>{this._now=Date.now(),this.requestUpdate()},6e4),"function"==typeof ResizeObserver&&(this._resizeObserver=new ResizeObserver(t=>{const e=t[0]?.contentRect.width??0;e!==this._width&&(this._width=e,this.requestUpdate())}),this._resizeObserver.observe(this)),this._hass&&this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._refreshTimer&&window.clearInterval(this._refreshTimer),null!==this._nowTimer&&window.clearInterval(this._nowTimer),this._refreshTimer=null,this._nowTimer=null,this._resizeObserver?.disconnect(),this._resizeObserver=null,this._generation+=1}async _load(){const t=this._hass;if(!t)return;const e=++this._generation;try{const s=await function(t){return t.callApi("GET","meteofrance_radar/pin_series")}(t);if(e!==this._generation)return;this._data=s,this._state="ready"}catch(t){if(e!==this._generation)return;console.warn("meteofrance-rain-bar-card: pin series failed",t),this._state="error"}this._now=Date.now(),this.requestUpdate()}render(){const t=Et(this._hass?.locale?.language??this._hass?.language);return Me({strings:ge(t),language:t,title:this._config.title,showLegend:this._config.show_legend,state:this._state,data:this._data,now:this._now,timeZone:this._hass?.config?.time_zone,maxLabels:(e=this._width,e>0&&e<360?4:8)});var e}}Te.styles=Ce;const Pe="https://github.com/fabienvauchelles/meteofrance-radar-ha";function Ie(t){const e=window;e.customCards=e.customCards??[],e.customCards.some(e=>e.type===t.type)||e.customCards.push(t)}const Ue="meteofrance-radar-card";customElements.get(Ue)||customElements.define(Ue,ae),Ie({type:Ue,name:"Météo-France Radar",description:"Plays the Météo-France rain radar over France, with a pin at your home.",preview:!0,documentationURL:Pe}),customElements.get(he)||customElements.define(he,Te),Ie({type:he,name:"Météo-France Rain Bar",description:"Rain at your home: the past 3 hours from the radar, then the forecast.",preview:!0,documentationURL:Pe});export{Ue as CARD_TAG,he as RAIN_BAR_TAG};
