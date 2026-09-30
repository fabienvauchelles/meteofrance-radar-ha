console.info("%c METEOFRANCE-RADAR-CARD %c 0.1.0 ","background:#1f5fa8;color:#fff;border-radius:3px","");const t=globalThis,e=t.ShadowRoot&&(void 0===t.ShadyCSS||t.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,s=Symbol(),i=new WeakMap;let n=class{constructor(t,e,i){if(this._$cssResult$=!0,i!==s)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=t,this.t=e}get styleSheet(){let t=this.o;const s=this.t;if(e&&void 0===t){const e=void 0!==s&&1===s.length;e&&(t=i.get(s)),void 0===t&&((this.o=t=new CSSStyleSheet).replaceSync(this.cssText),e&&i.set(s,t))}return t}toString(){return this.cssText}};const r=e?t=>t:t=>t instanceof CSSStyleSheet?(t=>{let e="";for(const s of t.cssRules)e+=s.cssText;return(t=>new n("string"==typeof t?t:t+"",void 0,s))(e)})(t):t,{is:o,defineProperty:a,getOwnPropertyDescriptor:h,getOwnPropertyNames:l,getOwnPropertySymbols:c,getPrototypeOf:d}=Object,p=globalThis,u=p.trustedTypes,m=u?u.emptyScript:"",f=p.reactiveElementPolyfillSupport,_=(t,e)=>t,g={toAttribute(t,e){switch(e){case Boolean:t=t?m:null;break;case Object:case Array:t=null==t?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=null!==t;break;case Number:s=null===t?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch(t){s=null}}return s}},$=(t,e)=>!o(t,e),b={attribute:!0,type:String,converter:g,reflect:!1,useDefault:!1,hasChanged:$};Symbol.metadata??=Symbol("metadata"),p.litPropertyMetadata??=new WeakMap;let y=class extends HTMLElement{static addInitializer(t){this._$Ei(),(this.l??=[]).push(t)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(t,e=b){if(e.state&&(e.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(t)&&((e=Object.create(e)).wrapped=!0),this.elementProperties.set(t,e),!e.noAccessor){const s=Symbol(),i=this.getPropertyDescriptor(t,s,e);void 0!==i&&a(this.prototype,t,i)}}static getPropertyDescriptor(t,e,s){const{get:i,set:n}=h(this.prototype,t)??{get(){return this[e]},set(t){this[e]=t}};return{get:i,set(e){const r=i?.call(this);n?.call(this,e),this.requestUpdate(t,r,s)},configurable:!0,enumerable:!0}}static getPropertyOptions(t){return this.elementProperties.get(t)??b}static _$Ei(){if(this.hasOwnProperty(_("elementProperties")))return;const t=d(this);t.finalize(),void 0!==t.l&&(this.l=[...t.l]),this.elementProperties=new Map(t.elementProperties)}static finalize(){if(this.hasOwnProperty(_("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(_("properties"))){const t=this.properties,e=[...l(t),...c(t)];for(const s of e)this.createProperty(s,t[s])}const t=this[Symbol.metadata];if(null!==t){const e=litPropertyMetadata.get(t);if(void 0!==e)for(const[t,s]of e)this.elementProperties.set(t,s)}this._$Eh=new Map;for(const[t,e]of this.elementProperties){const s=this._$Eu(t,e);void 0!==s&&this._$Eh.set(s,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(t){const e=[];if(Array.isArray(t)){const s=new Set(t.flat(1/0).reverse());for(const t of s)e.unshift(r(t))}else void 0!==t&&e.push(r(t));return e}static _$Eu(t,e){const s=e.attribute;return!1===s?void 0:"string"==typeof s?s:"string"==typeof t?t.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(t=>t(this))}addController(t){(this._$EO??=new Set).add(t),void 0!==this.renderRoot&&this.isConnected&&t.hostConnected?.()}removeController(t){this._$EO?.delete(t)}_$E_(){const t=new Map,e=this.constructor.elementProperties;for(const s of e.keys())this.hasOwnProperty(s)&&(t.set(s,this[s]),delete this[s]);t.size>0&&(this._$Ep=t)}createRenderRoot(){const s=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return((s,i)=>{if(e)s.adoptedStyleSheets=i.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const e of i){const i=document.createElement("style"),n=t.litNonce;void 0!==n&&i.setAttribute("nonce",n),i.textContent=e.cssText,s.appendChild(i)}})(s,this.constructor.elementStyles),s}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(t=>t.hostConnected?.())}enableUpdating(t){}disconnectedCallback(){this._$EO?.forEach(t=>t.hostDisconnected?.())}attributeChangedCallback(t,e,s){this._$AK(t,s)}_$ET(t,e){const s=this.constructor.elementProperties.get(t),i=this.constructor._$Eu(t,s);if(void 0!==i&&!0===s.reflect){const n=(void 0!==s.converter?.toAttribute?s.converter:g).toAttribute(e,s.type);this._$Em=t,null==n?this.removeAttribute(i):this.setAttribute(i,n),this._$Em=null}}_$AK(t,e){const s=this.constructor,i=s._$Eh.get(t);if(void 0!==i&&this._$Em!==i){const t=s.getPropertyOptions(i),n="function"==typeof t.converter?{fromAttribute:t.converter}:void 0!==t.converter?.fromAttribute?t.converter:g;this._$Em=i;const r=n.fromAttribute(e,t.type);this[i]=r??this._$Ej?.get(i)??r,this._$Em=null}}requestUpdate(t,e,s,i=!1,n){if(void 0!==t){const r=this.constructor;if(!1===i&&(n=this[t]),s??=r.getPropertyOptions(t),!((s.hasChanged??$)(n,e)||s.useDefault&&s.reflect&&n===this._$Ej?.get(t)&&!this.hasAttribute(r._$Eu(t,s))))return;this.C(t,e,s)}!1===this.isUpdatePending&&(this._$ES=this._$EP())}C(t,e,{useDefault:s,reflect:i,wrapped:n},r){s&&!(this._$Ej??=new Map).has(t)&&(this._$Ej.set(t,r??e??this[t]),!0!==n||void 0!==r)||(this._$AL.has(t)||(this.hasUpdated||s||(e=void 0),this._$AL.set(t,e)),!0===i&&this._$Em!==t&&(this._$Eq??=new Set).add(t))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const t=this.scheduleUpdate();return null!=t&&await t,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(const[t,e]of this._$Ep)this[t]=e;this._$Ep=void 0}const t=this.constructor.elementProperties;if(t.size>0)for(const[e,s]of t){const{wrapped:t}=s,i=this[e];!0!==t||this._$AL.has(e)||void 0===i||this.C(e,void 0,s,i)}}let t=!1;const e=this._$AL;try{t=this.shouldUpdate(e),t?(this.willUpdate(e),this._$EO?.forEach(t=>t.hostUpdate?.()),this.update(e)):this._$EM()}catch(e){throw t=!1,this._$EM(),e}t&&this._$AE(e)}willUpdate(t){}_$AE(t){this._$EO?.forEach(t=>t.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(t)),this.updated(t)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(t){return!0}update(t){this._$Eq&&=this._$Eq.forEach(t=>this._$ET(t,this[t])),this._$EM()}updated(t){}firstUpdated(t){}};y.elementStyles=[],y.shadowRootOptions={mode:"open"},y[_("elementProperties")]=new Map,y[_("finalized")]=new Map,f?.({ReactiveElement:y}),(p.reactiveElementVersions??=[]).push("2.1.2");const w=globalThis,v=t=>t,A=w.trustedTypes,x=A?A.createPolicy("lit-html",{createHTML:t=>t}):void 0,k="$lit$",E=`lit$${Math.random().toFixed(9).slice(2)}$`,S="?"+E,C=`<${S}>`,M=document,P=()=>M.createComment(""),T=t=>null===t||"object"!=typeof t&&"function"!=typeof t,U=Array.isArray,O="[ \t\n\f\r]",I=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,H=/-->/g,R=/>/g,N=RegExp(`>|${O}(?:([^\\s"'>=/]+)(${O}*=${O}*(?:[^ \t\n\f\r"'\`<>=]|("|')|))|$)`,"g"),q=/'/g,B=/"/g,D=/^(?:script|style|textarea|title)$/i,j=(t=>(e,...s)=>({_$litType$:t,strings:e,values:s}))(1),z=Symbol.for("lit-noChange"),F=Symbol.for("lit-nothing"),L=new WeakMap,G=M.createTreeWalker(M,129);function W(t,e){if(!U(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return void 0!==x?x.createHTML(e):e}const V=(t,e)=>{const s=t.length-1,i=[];let n,r=2===e?"<svg>":3===e?"<math>":"",o=I;for(let e=0;e<s;e++){const s=t[e];let a,h,l=-1,c=0;for(;c<s.length&&(o.lastIndex=c,h=o.exec(s),null!==h);)c=o.lastIndex,o===I?"!--"===h[1]?o=H:void 0!==h[1]?o=R:void 0!==h[2]?(D.test(h[2])&&(n=RegExp("</"+h[2],"g")),o=N):void 0!==h[3]&&(o=N):o===N?">"===h[0]?(o=n??I,l=-1):void 0===h[1]?l=-2:(l=o.lastIndex-h[2].length,a=h[1],o=void 0===h[3]?N:'"'===h[3]?B:q):o===B||o===q?o=N:o===H||o===R?o=I:(o=N,n=void 0);const d=o===N&&t[e+1].startsWith("/>")?" ":"";r+=o===I?s+C:l>=0?(i.push(a),s.slice(0,l)+k+s.slice(l)+E+d):s+E+(-2===l?e:d)}return[W(t,r+(t[s]||"<?>")+(2===e?"</svg>":3===e?"</math>":"")),i]};class K{constructor({strings:t,_$litType$:e},s){let i;this.parts=[];let n=0,r=0;const o=t.length-1,a=this.parts,[h,l]=V(t,e);if(this.el=K.createElement(h,s),G.currentNode=this.el.content,2===e||3===e){const t=this.el.content.firstChild;t.replaceWith(...t.childNodes)}for(;null!==(i=G.nextNode())&&a.length<o;){if(1===i.nodeType){if(i.hasAttributes())for(const t of i.getAttributeNames())if(t.endsWith(k)){const e=l[r++],s=i.getAttribute(t).split(E),o=/([.?@])?(.*)/.exec(e);a.push({type:1,index:n,name:o[2],strings:s,ctor:"."===o[1]?Y:"?"===o[1]?tt:"@"===o[1]?et:X}),i.removeAttribute(t)}else t.startsWith(E)&&(a.push({type:6,index:n}),i.removeAttribute(t));if(D.test(i.tagName)){const t=i.textContent.split(E),e=t.length-1;if(e>0){i.textContent=A?A.emptyScript:"";for(let s=0;s<e;s++)i.append(t[s],P()),G.nextNode(),a.push({type:2,index:++n});i.append(t[e],P())}}}else if(8===i.nodeType)if(i.data===S)a.push({type:2,index:n});else{let t=-1;for(;-1!==(t=i.data.indexOf(E,t+1));)a.push({type:7,index:n}),t+=E.length-1}n++}}static createElement(t,e){const s=M.createElement("template");return s.innerHTML=t,s}}function Z(t,e,s=t,i){if(e===z)return e;let n=void 0!==i?s._$Co?.[i]:s._$Cl;const r=T(e)?void 0:e._$litDirective$;return n?.constructor!==r&&(n?._$AO?.(!1),void 0===r?n=void 0:(n=new r(t),n._$AT(t,s,i)),void 0!==i?(s._$Co??=[])[i]=n:s._$Cl=n),void 0!==n&&(e=Z(t,n._$AS(t,e.values),n,i)),e}class J{constructor(t,e){this._$AV=[],this._$AN=void 0,this._$AD=t,this._$AM=e}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(t){const{el:{content:e},parts:s}=this._$AD,i=(t?.creationScope??M).importNode(e,!0);G.currentNode=i;let n=G.nextNode(),r=0,o=0,a=s[0];for(;void 0!==a;){if(r===a.index){let e;2===a.type?e=new Q(n,n.nextSibling,this,t):1===a.type?e=new a.ctor(n,a.name,a.strings,this,t):6===a.type&&(e=new st(n,this,t)),this._$AV.push(e),a=s[++o]}r!==a?.index&&(n=G.nextNode(),r++)}return G.currentNode=M,i}p(t){let e=0;for(const s of this._$AV)void 0!==s&&(void 0!==s.strings?(s._$AI(t,s,e),e+=s.strings.length-2):s._$AI(t[e])),e++}}class Q{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(t,e,s,i){this.type=2,this._$AH=F,this._$AN=void 0,this._$AA=t,this._$AB=e,this._$AM=s,this.options=i,this._$Cv=i?.isConnected??!0}get parentNode(){let t=this._$AA.parentNode;const e=this._$AM;return void 0!==e&&11===t?.nodeType&&(t=e.parentNode),t}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(t,e=this){t=Z(this,t,e),T(t)?t===F||null==t||""===t?(this._$AH!==F&&this._$AR(),this._$AH=F):t!==this._$AH&&t!==z&&this._(t):void 0!==t._$litType$?this.$(t):void 0!==t.nodeType?this.T(t):(t=>U(t)||"function"==typeof t?.[Symbol.iterator])(t)?this.k(t):this._(t)}O(t){return this._$AA.parentNode.insertBefore(t,this._$AB)}T(t){this._$AH!==t&&(this._$AR(),this._$AH=this.O(t))}_(t){this._$AH!==F&&T(this._$AH)?this._$AA.nextSibling.data=t:this.T(M.createTextNode(t)),this._$AH=t}$(t){const{values:e,_$litType$:s}=t,i="number"==typeof s?this._$AC(t):(void 0===s.el&&(s.el=K.createElement(W(s.h,s.h[0]),this.options)),s);if(this._$AH?._$AD===i)this._$AH.p(e);else{const t=new J(i,this),s=t.u(this.options);t.p(e),this.T(s),this._$AH=t}}_$AC(t){let e=L.get(t.strings);return void 0===e&&L.set(t.strings,e=new K(t)),e}k(t){U(this._$AH)||(this._$AH=[],this._$AR());const e=this._$AH;let s,i=0;for(const n of t)i===e.length?e.push(s=new Q(this.O(P()),this.O(P()),this,this.options)):s=e[i],s._$AI(n),i++;i<e.length&&(this._$AR(s&&s._$AB.nextSibling,i),e.length=i)}_$AR(t=this._$AA.nextSibling,e){for(this._$AP?.(!1,!0,e);t!==this._$AB;){const e=v(t).nextSibling;v(t).remove(),t=e}}setConnected(t){void 0===this._$AM&&(this._$Cv=t,this._$AP?.(t))}}class X{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(t,e,s,i,n){this.type=1,this._$AH=F,this._$AN=void 0,this.element=t,this.name=e,this._$AM=i,this.options=n,s.length>2||""!==s[0]||""!==s[1]?(this._$AH=Array(s.length-1).fill(new String),this.strings=s):this._$AH=F}_$AI(t,e=this,s,i){const n=this.strings;let r=!1;if(void 0===n)t=Z(this,t,e,0),r=!T(t)||t!==this._$AH&&t!==z,r&&(this._$AH=t);else{const i=t;let o,a;for(t=n[0],o=0;o<n.length-1;o++)a=Z(this,i[s+o],e,o),a===z&&(a=this._$AH[o]),r||=!T(a)||a!==this._$AH[o],a===F?t=F:t!==F&&(t+=(a??"")+n[o+1]),this._$AH[o]=a}r&&!i&&this.j(t)}j(t){t===F?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,t??"")}}class Y extends X{constructor(){super(...arguments),this.type=3}j(t){this.element[this.name]=t===F?void 0:t}}class tt extends X{constructor(){super(...arguments),this.type=4}j(t){this.element.toggleAttribute(this.name,!!t&&t!==F)}}class et extends X{constructor(t,e,s,i,n){super(t,e,s,i,n),this.type=5}_$AI(t,e=this){if((t=Z(this,t,e,0)??F)===z)return;const s=this._$AH,i=t===F&&s!==F||t.capture!==s.capture||t.once!==s.once||t.passive!==s.passive,n=t!==F&&(s===F||i);i&&this.element.removeEventListener(this.name,this,s),n&&this.element.addEventListener(this.name,this,t),this._$AH=t}handleEvent(t){"function"==typeof this._$AH?this._$AH.call(this.options?.host??this.element,t):this._$AH.handleEvent(t)}}class st{constructor(t,e,s){this.element=t,this.type=6,this._$AN=void 0,this._$AM=e,this.options=s}get _$AU(){return this._$AM._$AU}_$AI(t){Z(this,t)}}const it=w.litHtmlPolyfillSupport;it?.(K,Q),(w.litHtmlVersions??=[]).push("3.3.3");const nt=globalThis;let rt=class extends y{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){const t=super.createRenderRoot();return this.renderOptions.renderBefore??=t.firstChild,t}update(t){const e=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(t),this._$Do=((t,e,s)=>{const i=s?.renderBefore??e;let n=i._$litPart$;if(void 0===n){const t=s?.renderBefore??null;i._$litPart$=n=new Q(e.insertBefore(P(),t),t,void 0,s??{})}return n._$AI(t),n})(e,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return z}};rt._$litElement$=!0,rt.finalized=!0,nt.litElementHydrateSupport?.({LitElement:rt});const ot=nt.litElementPolyfillSupport;ot?.({LitElement:rt}),(nt.litElementVersions??=[]).push("4.2.2");const at=1,ht=2,lt=t=>(...e)=>({_$litDirective$:t,values:e});let ct=class{constructor(t){}get _$AU(){return this._$AM._$AU}_$AT(t,e,s){this._$Ct=t,this._$AM=e,this._$Ci=s}_$AS(t,e){return this.update(t,e)}update(t,e){return this.render(...e)}};const dt=(t,e)=>{const s=t._$AN;if(void 0===s)return!1;for(const t of s)t._$AO?.(e,!1),dt(t,e);return!0},pt=t=>{let e,s;do{if(void 0===(e=t._$AM))break;s=e._$AN,s.delete(t),t=e}while(0===s?.size)},ut=t=>{for(let e;e=t._$AM;t=e){let s=e._$AN;if(void 0===s)e._$AN=s=new Set;else if(s.has(t))break;s.add(t),_t(e)}};function mt(t){void 0!==this._$AN?(pt(this),this._$AM=t,ut(this)):this._$AM=t}function ft(t,e=!1,s=0){const i=this._$AH,n=this._$AN;if(void 0!==n&&0!==n.size)if(e)if(Array.isArray(i))for(let t=s;t<i.length;t++)dt(i[t],!1),pt(i[t]);else null!=i&&(dt(i,!1),pt(i));else dt(this,t)}const _t=t=>{t.type==ht&&(t._$AP??=ft,t._$AQ??=mt)};class gt extends ct{constructor(){super(...arguments),this._$AN=void 0}_$AT(t,e,s){super._$AT(t,e,s),ut(this),this.isConnected=t._$AU}_$AO(t,e=!0){t!==this.isConnected&&(this.isConnected=t,t?this.reconnected?.():this.disconnected?.()),e&&(dt(this,t),pt(this))}setValue(t){if((t=>void 0===t.strings)(this._$Ct))this._$Ct._$AI(t,this);else{const e=[...this._$Ct._$AH];e[this._$Ci]=t,this._$Ct._$AI(e,this,0)}}disconnected(){}reconnected(){}}class $t{}const bt=new WeakMap,yt=lt(class extends gt{render(t){return F}update(t,[e]){const s=e!==this.G;return s&&this.rt(void 0),(s||this.lt!==this.ct)&&(this.G=e,this.ht=t.options?.host,this.rt(this.ct=t.element)),F}rt(t){if(void 0!==this.G)if(this.isConnected||(t=void 0),"function"==typeof this.G){const e=this.ht??globalThis;let s=bt.get(e);void 0===s&&(s=new WeakMap,bt.set(e,s)),void 0!==s.get(this.G)&&this.G.call(this.ht,void 0),s.set(this.G,t),void 0!==t&&this.G.call(this.ht,t)}else this.G.value=t}get lt(){return"function"==typeof this.G?bt.get(this.ht??globalThis)?.get(this.G):this.G?.value}disconnected(){this.lt===this.ct&&this.rt(void 0)}reconnected(){this.rt(this.ct)}});class wt extends Error{constructor(t,e){super(t),this.status=e,this.name="RadarApiError"}}class vt{constructor(t){this.hass=t}get client(){const t=this.hass();if(!t)throw new wt("Home Assistant is not connected",null);return t}frames(t){return this.client.callApi("GET",`meteofrance_radar/frames?period=${t}`)}async blob(t){const e=await this.client.fetchWithAuth(t);if(!e.ok)throw new wt(`${t}: HTTP ${e.status}`,e.status);return e.blob()}}class At{constructor(t,e,s,i){this.canvas=t,this.width=e,this.height=s,this.contextOf=i,this.basemap=null,t.width=e,t.height=s,this.context=i(t),this.slots=[this.makeSlot(),this.makeSlot()]}matches(t,e,s){return this.canvas===t&&this.width===e&&this.height===s}setBasemap(t){this.basemap=t,this.reset()}reset(){for(const t of this.slots)t.key=null}drawBasemap(){const t=this.context;t&&(t.globalAlpha=1,t.clearRect(0,0,this.width,this.height),this.basemap&&t.drawImage(this.basemap,0,0,this.width,this.height))}draw(t,e,s){const i=this.context;if(!i)return;const n=this.composite(t,e?.key??null);if(i.globalAlpha=1,i.clearRect(0,0,this.width,this.height),i.drawImage(n,0,0),null===e||s<=0)return;const r=this.composite(e,t.key);i.globalAlpha=Math.min(1,s),i.drawImage(r,0,0),i.globalAlpha=1}makeSlot(){const t=document.createElement("canvas");return t.width=this.width,t.height=this.height,{key:null,canvas:t}}composite(t,e){const s=this.slots.find(e=>e.key===t.key);if(s)return s.canvas;const i=this.slots.find(t=>t.key!==e)??this.slots[0],n=this.contextOf(i.canvas);return n&&(n.globalAlpha=1,n.clearRect(0,0,this.width,this.height),this.basemap&&n.drawImage(this.basemap,0,0,this.width,this.height),n.drawImage(t.bitmap,0,0,this.width,this.height)),i.key=t.key,i.canvas}}const xt=["3h","24h","7d","30d","all"];const kt={default_period:"3h",autoplay:!0,show_legend:!0,frame_duration_ms:500,crossfade_ms:300},Et=new Set(["type","grid_options","layout_options","view_layout","visibility",...Object.keys(kt)]);class St extends Error{constructor(t){super(t),this.name="CardConfigError"}}function Ct(t,e){const s=t[e];if(void 0===s)return kt[e];if("boolean"!=typeof s)throw new St(`${e} must be true or false`);return s}function Mt(t,e,s,i){const n=t[e];if(void 0===n)return kt[e];if("number"!=typeof n||!Number.isFinite(n)||n<s||n>i)throw new St(`${e} must be a number from ${s} to ${i}`);return Math.round(n)}function Pt(t){if(null===t||"object"!=typeof t)throw new St("the card config must be an object");for(const e of Object.keys(t))if(!Et.has(e))throw new St(`unknown option: ${e}`);const e=t.default_period??kt.default_period;if(!xt.includes(e))throw new St(`default_period must be one of ${xt.join(", ")}`);const s=Mt(t,"frame_duration_ms",100,5e3),i=Mt(t,"crossfade_ms",0,2e3);return{default_period:e,autoplay:Ct(t,"autoplay"),show_legend:Ct(t,"show_legend"),frame_duration_ms:s,crossfade_ms:Math.min(i,s)}}const Tt={credit:"Météo-France data",gap:t=>`gap of ${t} min skipped`,loading:"Loading the radar...",empty:"No radar image yet. The first one shows up a few minutes after setup.",error:"Could not load the radar images. Trying again in a minute.",play:"Play",pause:"Pause",stepBack:"Previous image",stepForward:"Next image",timeSlider:"Time",periods:{"3h":"3 h","24h":"24 h","7d":"7 d","30d":"30 d",all:"All"},periodGroup:"Period",pin:"Home",noData:"no data",legend:"Rain rate",attribution:(t,e)=>`Radar: ${t} | Basemap: ${e}`,form:{default_period:"Default period",autoplay:"Play on load",show_legend:"Show the legend",frame_duration_ms:"Time on each image (ms)",crossfade_ms:"Crossfade (ms)",frameHelper:"From 100 to 5000 ms.",crossfadeHelper:"From 0 to 2000 ms, never longer than the time on each image."}},Ut={credit:"Données Météo-France",gap:t=>`saut de ${t} min`,loading:"Chargement du radar...",empty:"Pas encore d'image radar. La première arrive quelques minutes après l'installation.",error:"Impossible de charger les images radar. Nouvel essai dans une minute.",play:"Lecture",pause:"Pause",stepBack:"Image précédente",stepForward:"Image suivante",timeSlider:"Heure",periods:{"3h":"3 h","24h":"24 h","7d":"7 j","30d":"30 j",all:"Tout"},periodGroup:"Période",pin:"Maison",noData:"pas de données",legend:"Intensité de pluie",attribution:(t,e)=>`Radar : ${t} | Fond de carte : ${e}`,form:{default_period:"Période par défaut",autoplay:"Lecture automatique",show_legend:"Afficher la légende",frame_duration_ms:"Durée de chaque image (ms)",crossfade_ms:"Fondu enchaîné (ms)",frameHelper:"De 100 à 5000 ms.",crossfadeHelper:"De 0 à 2000 ms, jamais plus que la durée de chaque image."}};function Ot(t){return t?.toLowerCase().startsWith("fr")?"fr":"en"}function It(t){return"fr"===Ot(t)?Ut:Tt}const Ht=new Map;function Rt(t,e,s){const i={};for(const s of function(t){const e=t??"",s=Ht.get(e);if(s)return s;const i={hourCycle:"h23",day:"2-digit",month:"2-digit",year:"2-digit",hour:"2-digit",minute:"2-digit"};let n;try{n=new Intl.DateTimeFormat("en-GB",{...i,timeZone:t})}catch{n=new Intl.DateTimeFormat("en-GB",i)}return Ht.set(e,n),n}(e).formatToParts(new Date(t)))i[s.type]=s.value;const n="fr"===Ot(s)?"h":":";return`${i.day}/${i.month}/${i.year} ${i.hour}${n}${i.minute}`}function Nt(t,e,s,i){const n=[];for(let r=s;r<=i&&r<t.length;r+=1){const s=t[(e+r)%t.length];void 0!==s&&n.push(s)}return n}class qt{constructor(t){this.deps=t,this.blobs=new Map,this.pending=new Map,this.queue=[],this.active=0,this.bitmaps=new Map,this.decoding=new Map,this.wanted=new Set,this.windowKey="",this.closed=!1,this.failed=new Map}blob(t,e=!0){const s=this.blobs.get(t);if(s)return this.blobs.delete(t),this.blobs.set(t,s),Promise.resolve(s);const i=this.failed.get(t);if(i&&Date.now()-i.at<3e5)return Promise.reject(i.error);this.failed.delete(t);const n=this.pending.get(t);if(n)return e&&this.promote(t),n;const r=new Promise((s,i)=>{const n={url:t,resolve:s,reject:i};e?this.queue.unshift(n):this.queue.push(n)});return this.pending.set(t,r),this.pump(),r}prefetch(t){for(const e of t)this.blob(e,!1).catch(()=>{})}setWindow(t){this.wanted=new Set(t);for(const[t,e]of this.bitmaps)this.wanted.has(t)||(e.close(),this.bitmaps.delete(t));for(const e of t)this.decode(e).catch(()=>{})}focus(t,e){const s=Nt(t,e,0,3),i=s.join("|");i!==this.windowKey&&(this.windowKey=i,this.setWindow(s),this.prefetch(Nt(t,e,4,11)))}async ensure(t){await Promise.all(t.map(t=>this.decode(t)))}bitmap(t){return this.bitmaps.get(t)??null}close(){this.closed=!0;for(const t of this.queue)t.reject(new Error("loader closed"));this.queue.length=0;for(const t of this.bitmaps.values())t.close();this.bitmaps.clear()}decode(t){const e=this.bitmaps.get(t);if(e)return Promise.resolve(e);const s=this.decoding.get(t);if(s)return s;const i=this.blob(t).then(t=>this.deps.decode(t)).then(e=>(this.closed||!this.wanted.has(t)?e.close():this.bitmaps.set(t,e),e)).finally(()=>this.decoding.delete(t));return this.decoding.set(t,i),i}promote(t){const e=this.queue.findIndex(e=>e.url===t);if(e<=0)return;const[s]=this.queue.splice(e,1);s&&this.queue.unshift(s)}pump(){for(;!this.closed&&this.active<4;){const t=this.queue.shift();if(!t)return;this.active+=1,this.deps.fetchBlob(t.url).then(e=>{this.remember(t.url,e),t.resolve(e)},e=>{this.failed.set(t.url,{at:Date.now(),error:e}),t.reject(e)}).finally(()=>{this.pending.delete(t.url),this.active-=1,this.pump()})}}remember(t,e){this.blobs.set(t,e);for(const t of this.blobs.keys()){if(this.blobs.size<=300)return;this.blobs.delete(t)}}}function Bt(t,e,s){return s<=0?0:((t+e)%s+s)%s}function Dt(t,e,s){const i=t[s],n=i?e[i.frame]:void 0;return i&&void 0!==n?[n,null===i.next?null:e[i.next]??null]:null}class jt{constructor(t,e){this.hooks=t,this.clock=e,this.stepIndex=0,this.playing=!1,this.waiting=!1,this.elapsed=0,this.resumeAfterScrub=!1,this.lastTick=null,this.handle=null}play(){this.playing||0===this.hooks.steps().length||(this.playing=!0,this.lastTick=null,this.schedule(),this.hooks.changed())}pause(){null!==this.handle&&this.clock.cancelFrame(this.handle),this.handle=null,this.playing&&(this.playing=!1,this.hooks.changed())}toggle(){this.playing?this.pause():this.play()}moveTo(t){this.stepIndex=t,this.elapsed=0,this.lastTick=null}async seek(t){this.moveTo(t),this.hooks.changed(),this.hooks.render(t,0)||(await this.hooks.ensure(t),this.stepIndex===t&&0===this.elapsed&&this.hooks.render(t,0))}stepBy(t){return this.pause(),this.seek(Bt(this.stepIndex,t,this.hooks.steps().length))}scrub(t){return this.playing&&(this.resumeAfterScrub=!0,this.pause()),this.seek(t)}scrubEnd(){this.resumeAfterScrub&&this.play(),this.resumeAfterScrub=!1}schedule(){this.handle=this.clock.requestFrame(()=>this.tick())}tick(){if(this.handle=null,!this.playing||0===this.hooks.steps().length)return;const t=this.clock.now(),e=null===this.lastTick?0:t-this.lastTick;this.lastTick=t,this.waiting||this.advance(e),this.schedule()}advance(t){const e=this.hooks.steps(),s=this.stepIndex;this.stepIndex=Math.min(this.stepIndex,e.length-1),this.elapsed+=t;let i=e[this.stepIndex];for(;i&&this.elapsed>=i.durationMs;)this.elapsed-=i.durationMs,this.stepIndex=Bt(this.stepIndex,1,e.length),i=e[this.stepIndex];i&&(this.stepIndex!==s&&this.hooks.changed(),this.hooks.render(this.stepIndex,function(t,e){if(null===t.next||t.fadeMs<=0)return 0;const s=t.durationMs-t.fadeMs;return e<=s?0:Math.min(1,(e-s)/t.fadeMs)}(i,this.elapsed))||this.wait(this.stepIndex))}wait(t){this.waiting=!0,this.hooks.changed(),this.hooks.ensure(t).catch(()=>{this.stepIndex===t&&this.moveTo(Bt(t,1,this.hooks.steps().length))}).finally(()=>{this.waiting=!1,this.lastTick=null,this.hooks.changed()})}}const zt=((t,...e)=>{const i=1===t.length?t[0]:e.reduce((e,s,i)=>e+(t=>{if(!0===t._$cssResult$)return t.cssText;if("number"==typeof t)return t;throw Error("Value passed to 'css' function must be a 'css' function result: "+t+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(s)+t[i+1],t[0]);return new n(i,t,s)})`
  :host {
    display: block;
  }
  ha-card {
    overflow: hidden;
    padding-bottom: 8px;
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
    align-items: center;
    gap: 4px;
    padding: 8px 12px 0;
  }
  .controls input[type="range"] {
    flex: 1;
    min-width: 0;
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
`,Ft="important",Lt=" !"+Ft,Gt=lt(class extends ct{constructor(t){if(super(t),t.type!==at||"style"!==t.name||t.strings?.length>2)throw Error("The `styleMap` directive must be used in the `style` attribute and must be the only part in the attribute.")}render(t){return Object.keys(t).reduce((e,s)=>{const i=t[s];return null==i?e:e+`${s=s.includes("-")?s:s.replace(/(?:^(webkit|moz|ms|o)|)(?=[A-Z])/g,"-$&").toLowerCase()}:${i};`},"")}update(t,[e]){const{style:s}=t.element;if(void 0===this.ft)return this.ft=new Set(Object.keys(e)),this.render(e);for(const t of this.ft)null==e[t]&&(this.ft.delete(t),t.includes("-")?s.removeProperty(t):s[t]=null);for(const t in e){const i=e[t];if(null!=i){this.ft.add(t);const e="string"==typeof i&&i.endsWith(Lt);t.includes("-")||e?s.setProperty(t,e?i.slice(0,-11):i,e?Ft:""):s[t]=i}}return z}});function Wt(t,e,s){return j`
    <div class="legend" role="list" aria-label=${e.legend}>
      <span class="legend-unit">${t.unit}</span>
      ${t.colors.map((e,i)=>j`
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
  `}function Vt(t){const e=t?.pin;return t&&e?.inside?{left:e.x/t.grid.width*100,top:e.y/t.grid.height*100}:null}function Kt(t,e){const s=t.pin,i=s?{left:`${s.left}%`,top:`${s.top}%`}:{};return j`
    <div class="stage" style=${Gt({"aspect-ratio":String(t.aspect)})}>
      <canvas ${yt(e.canvasRef)}></canvas>
      <div
        class="pin"
        title=${t.strings.pin}
        ?hidden=${null===s}
        style=${Gt(i)}
      ></div>
      ${function(t){const{strings:e}=t;return"loading"===t.state?j`<div class="message">${e.loading}</div>`:"empty"===t.state?j`<div class="message empty">${e.empty}</div>`:"error"===t.state?j`<div class="message error" role="alert">${e.error}</div>`:F}(t)}
    </div>
  `}function Zt(t,e){const s=t.attribution;return j`
    <ha-card>
      ${function(t){const{strings:e}=t;return j`
    <div class="title">
      ${t.time?j`<span class="time">${t.time}</span>`:F}
      <span class="credit">${e.credit}</span>
      ${t.gapMin>0?j`<span class="gap" role="note">${e.gap(t.gapMin)}</span>`:F}
    </div>
  `}(t)} ${Kt(t,e)} ${function(t,e){const{strings:s}=t,i=0===t.count;return j`
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
      <input
        type="range"
        min="0"
        max=${Math.max(0,t.count-1)}
        step="1"
        aria-label=${s.timeSlider}
        ?disabled=${i}
        .value=${String(t.position)}
        @input=${t=>e.scrub(Number(t.target.value))}
        @change=${e.scrubEnd}
      />
    </div>
  `}(t,e)}
      ${function(t,e){return j`
    <div class="periods" role="group" aria-label=${t.strings.periodGroup}>
      ${xt.map(s=>j`
          <button
            class="chip"
            data-period=${s}
            aria-pressed=${t.period===s?"true":"false"}
            @click=${()=>e.selectPeriod(s)}
          >${t.strings.periods[s]}</button>
        `)}
    </div>
  `}(t,e)}
      ${t.legend?Wt(t.legend,t.strings,t.language):F}
      ${s?j`<div class="attribution">
              ${t.strings.attribution(s.radar,s.basemap)}
            </div>`:F}
    </ha-card>
  `}class Jt extends rt{constructor(){super(...arguments),this.seams=function(){const t="function"==typeof requestAnimationFrame;return{createImageBitmap:t=>createImageBitmap(t),context2d:t=>t.getContext("2d"),now:()=>performance.now(),requestFrame:e=>t?requestAnimationFrame(()=>e()):window.setTimeout(e,16),cancelFrame:e=>t?cancelAnimationFrame(e):clearTimeout(e)}}(),this._period=kt.default_period,this._data=null,this._state="loading",this._steps=[],this._shown=0,this._generation=0,this._refreshTimer=null,this._resumeOnConnect=!1,this._basemapUrl=null,this._basemap=null,this._compositor=null,this._canvasRef=new $t,this._api=new vt(()=>this._hass),this._loader=new qt({fetchBlob:t=>this._api.blob(t),decode:t=>this.seams.createImageBitmap(t)}),this._playback=new jt({steps:()=>this._steps,render:(t,e)=>this._render(t,e),ensure:t=>this._ensure(t),changed:()=>this.requestUpdate()},{now:()=>this.seams.now(),requestFrame:t=>this.seams.requestFrame(t),cancelFrame:t=>this.seams.cancelFrame(t)})}static getConfigForm(){return function(t){const e=It(t),s=e.form,i=[{name:"default_period",selector:{select:{mode:"dropdown",options:xt.map(t=>({value:t,label:e.periods[t]}))}}},{name:"autoplay",selector:{boolean:{}}},{name:"show_legend",selector:{boolean:{}}},{name:"frame_duration_ms",selector:{number:{min:100,max:5e3,step:100,mode:"box",unit_of_measurement:"ms"}}},{name:"crossfade_ms",selector:{number:{min:0,max:2e3,step:50,mode:"box",unit_of_measurement:"ms"}}}];for(const t of i)t.default=kt[t.name];const n={default_period:s.default_period,autoplay:s.autoplay,show_legend:s.show_legend,frame_duration_ms:s.frame_duration_ms,crossfade_ms:s.crossfade_ms},r={frame_duration_ms:s.frameHelper,crossfade_ms:s.crossfadeHelper};return{schema:i,computeLabel:t=>n[t.name],computeHelper:t=>r[t.name],assertConfig:t=>{Pt(t)}}}(function(){const t=document.querySelector("home-assistant");return t?.hass?.locale?.language??t?.hass?.language??navigator.language}())}static getStubConfig(){return{default_period:kt.default_period,autoplay:kt.autoplay}}setConfig(t){const e=Pt(t),s=this._config?.default_period!==e.default_period;this._config=e,this._steps=this._buildSteps(),s&&(this._period=e.default_period,this.isConnected&&this._load()),this.requestUpdate()}set hass(t){const e=this._hass;this._hass=t,e||!this.isConnected||this._data||this._load();const s=t=>t?.locale?.language??t?.language;s(e)===s(t)&&e?.config.time_zone===t.config.time_zone||this.requestUpdate()}get hass(){return this._hass}getCardSize(){return 7}getGridOptions(){return{columns:12,rows:"auto",min_columns:6}}connectedCallback(){super.connectedCallback(),this._refreshTimer=window.setInterval(()=>{this._refresh()},6e4),this._resumeOnConnect&&this._playback.play(),this._data?this._refresh():this._load()}disconnectedCallback(){super.disconnectedCallback(),null!==this._refreshTimer&&window.clearInterval(this._refreshTimer),this._refreshTimer=null,this._resumeOnConnect=this._playback.playing,this._playback.pause()}updated(){const t=this._canvasRef.value;if(!t)return;const e=this._data?.grid.width??1920,s=this._data?.grid.height??1080;this._compositor?.matches(t,e,s)||(this._compositor=new At(t,e,s,this.seams.context2d),this._compositor.setBasemap(this._basemap),this._compositor.drawBasemap())}render(){if(!this._config)return j``;const t=Ot(this._hass?.locale?.language??this._hass?.language),e=this._data,s="ready"===this._state?e?.frames[this._shown]:void 0;return Zt({strings:It(t),language:t,state:this._state,time:s?Rt(s.time,this._hass?.config.time_zone,t):null,gapMin:s?.gap_before_min??0,playing:this._playback.playing,waiting:this._playback.waiting,position:this._playback.stepIndex,count:"ready"===this._state?this._steps.length:0,period:this._period,pin:Vt(e),aspect:(e?.grid.width??1920)/(e?.grid.height??1080),legend:this._config.show_legend?e?.legend??null:null,attribution:e?.attribution??null},{canvasRef:this._canvasRef,togglePlay:()=>this._playback.toggle(),step:t=>{this._playback.stepBy(t).catch(Qt)},scrub:t=>{this._shown=t,this._playback.scrub(t).catch(Qt)},scrubEnd:()=>this._playback.scrubEnd(),selectPeriod:t=>this._selectPeriod(t)})}_buildSteps(){const t=this._config??kt;return function(t,e){const s=Math.max(1,e.frameMs),i=Math.max(0,Math.min(e.crossfadeMs,s));return t.map((e,n)=>{const r=t[n+1],o=void 0!==r&&r.gap_before_min<=0&&i>0;return{frame:n,next:o?n+1:null,durationMs:s,fadeMs:o?i:0}})}(this._data?.frames??[],{frameMs:t.frame_duration_ms,crossfadeMs:t.crossfade_ms})}_refresh(){const t="ready"===this._state?this._data?.frames[this._shown]?.time:void 0;return this._load(t??null,!0)}async _load(t=null,e=!1){if(!this._hass||!this._config)return;const s=++this._generation;e||(this._playback.pause(),this._state="loading",this.requestUpdate());try{const e=await this._api.frames(this._period);if(s!==this._generation)return;if(await this._loadBasemap(e.basemap),s!==this._generation)return;await this._install(e,t)}catch(t){if(s!==this._generation)return;console.warn("meteofrance-radar-card: frame list request failed",t),e&&this._data||(this._state="error",this.requestUpdate())}}async _loadBasemap(t){if(t!==this._basemapUrl)try{const e=await this.seams.createImageBitmap(await this._api.blob(t));this._basemap?.close(),this._basemap=e,this._basemapUrl=t,this._compositor?.setBasemap(e)}catch(t){console.warn("meteofrance-radar-card: basemap failed",t)}}async _install(t,e){this._data=t,this._steps=this._buildSteps(),this._compositor?.reset();const s=t.frames;if(0===s.length)return this._playback.pause(),this._state="empty",this.requestUpdate(),await this.updateComplete,void this._compositor?.drawBasemap();this._state="ready";const i=null===e&&(this._config?.autoplay??kt.autoplay),n=s.map(t=>t.time),r=null!==e?function(t,e){const s=Date.parse(e);let i=0;for(let e=0;e<t.length&&!(Date.parse(t[e]??"")>s);e+=1)i=e;return i}(n,e):i?0:s.length-1;this._shown=r,this._playback.playing&&r===this._playback.stepIndex||this._playback.moveTo(r),this.requestUpdate(),await this.updateComplete,this._playback.playing||(await this._playback.seek(r).catch(Qt),i&&this._playback.play())}_urls(){return(this._data?.frames??[]).map(t=>t.url)}_render(t,e){const s=Dt(this._steps,this._urls(),t),i=this._compositor;if(!s||!i)return!1;this._loader.focus(this._urls(),t);const[n,r]=s,o=this._loader.bitmap(n),a=null===r?null:this._loader.bitmap(r);if(!o||null!==r&&!a)return!1;const h=null!==r&&a?{key:r,bitmap:a}:null;i.draw({key:n,bitmap:o},h,e);const l=this._steps[t],c=l?function(t,e){return null!==t.next&&e>=.5?t.next:t.frame}(l,e):t;return c!==this._shown&&(this._shown=c,this.requestUpdate()),!0}_ensure(t){const e=Dt(this._steps,this._urls(),t);return e?(this._loader.focus(this._urls(),t),this._shown=t,this._loader.ensure(e.filter(t=>null!==t))):Promise.resolve()}_selectPeriod(t){t!==this._period&&(this._period=t,this._load())}}function Qt(t){console.warn("meteofrance-radar-card: layer failed",t)}Jt.styles=zt;const Xt="meteofrance-radar-card";customElements.get(Xt)||customElements.define(Xt,Jt);const Yt=window;Yt.customCards=Yt.customCards??[],Yt.customCards.some(t=>t.type===Xt)||Yt.customCards.push({type:Xt,name:"Météo-France Radar",description:"Plays the Météo-France rain radar over France, with a pin at your home.",preview:!0,documentationURL:"https://github.com/fabienvauchelles/meteofrance-radar-ha"});export{Xt as CARD_TAG};
