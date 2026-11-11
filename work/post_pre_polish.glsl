#version 330
uniform sampler2D S,S2,TX;
uniform vec2 R; uniform float T,flash,fade,kick,lod0;
uniform int trK; uniform float trX;
uniform vec4 dofA,dofB;   // focus, aperture, tilt amount, tilt centre
uniform vec4 pov;         // lens drops, lens snow, desat, edge blur
uniform vec4 fx;          // pulse zoom, radial blur, film, extra vignette
uniform vec4 grade;       // exposure, saturation, warmth, lift
out vec4 O;
float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
vec2 h22(vec2 p){float n=h21(p);return vec2(n,h21(p+n+7.7));}
float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+1.),f.x),f.y);}
float fbm(vec2 p){float a=.5,s=0.;for(int i=0;i<4;i++){s+=a*vn(p);p=p*2.02+7.;a*=.5;}return s;}
vec3 dofS(sampler2D s,vec2 u,vec4 d,float extra){
 float z=textureLod(s,u,lod0).a;
 float coc=d.y*abs(z-d.x)/max(z,.02)+d.z*abs(u.y-d.w)+extra;
 coc=min(coc,.05);
 float px=coc*textureSize(s,0).y;
 if(px<1.2)return textureLod(s,u,lod0).rgb;
 float lod=clamp(log2(px)-1.,lod0,6.);
 vec2 o=vec2(coc*R.y/R.x,coc)*.5;
 vec3 c=textureLod(s,u,lod).rgb*2.;
 c+=textureLod(s,u+o*vec2(.7,.7),lod).rgb+textureLod(s,u+o*vec2(-.7,.7),lod).rgb+textureLod(s,u+o*vec2(.7,-.7),lod).rgb+textureLod(s,u+o*vec2(-.7,-.7),lod).rgb;
 c+=textureLod(s,u+o*vec2(1.,0.),lod).rgb+textureLod(s,u+o*vec2(-1.,0.),lod).rgb+textureLod(s,u+o*vec2(0.,1.),lod).rgb+textureLod(s,u+o*vec2(0.,-1.),lod).rgb;
 return c/10.;}
vec3 scn(vec2 u,float extra){
 u=clamp(u,.001,.999);
 if(trK==0)return dofS(S,u,dofA,extra);
 vec3 a,b;
 if(trK==1){return mix(dofS(S,u,dofA,extra),dofS(S2,u,dofB,extra),trX);}
 if(trK==2){a=trX<.5?dofS(S,u,dofA,extra):dofS(S2,u,dofB,extra);return a+vec3(1.)*pow(1.-abs(2.*trX-1.),1.3)*3.;}
 if(trK==3){float n=fbm(u*vec2(3.,2.)+vec2(T*1.5,T*.4))+.3*(1.-u.x);float e=trX*1.9-.45;
  float m=smoothstep(e-.12,e+.12,n);a=dofS(S,u,dofA,extra);b=dofS(S2,u,dofB,extra);
  vec3 c=mix(b,a,m);c+=vec3(.55,.6,.68)*exp(-abs(n-e)*9.)*sin(3.1416*trX)*1.4;return c;}
 if(trK==4){float cs=cos(3.14159*trX);float y=.5+(u.y-.5)/max(abs(cs),.02);
  float rp=sin(y*50.+T*9.)*.012*sin(3.1416*trX);
  if(y<0.||y>1.)return vec3(.01,.02,.04);
  vec2 v=vec2(u.x+rp,trX<.5?y:y);
  vec3 c=trX<.5?dofS(S,v,dofA,extra):dofS(S2,v,dofB,extra);
  return c*(.35+.65*abs(cs));}
 if(trK==5){float x0=mix(1.25,-.3,trX);float w=.22;float xx=u.x+.05*sin(u.y*3.+1.);
  if(xx<x0)return dofS(S,u,dofA,extra);
  if(xx<x0+w){float k=(xx-x0)/w;vec3 bk=vec3(.82,.78,.7)*(.55+.45*sin(k*3.1416));
   vec3 src=dofS(S,vec2(2.*x0-u.x+w*k,u.y),dofA,.02);return mix(bk,src,.18);}
  b=dofS(S2,u,dofB,extra);return b*(1.-.5*exp(-(xx-x0-w)*9.));}
 return dofS(S,u,dofA,extra);}
void main(){
 vec2 uv=gl_FragCoord.xy/R;
 vec2 su=vec2(uv.x,1.-uv.y);
 vec2 cc=su-.5;float r2=dot(cc,cc);
 // pov: breathing / pulse zoom
 su=.5+cc*(1.-fx.x);
 // lens drops
 float wetm=0.;
 if(pov.x>0.){vec2 g=su*vec2(9.,5.);
  for(int k=0;k<2;k++){vec2 gg=g*(1.+float(k)*.7)+float(k)*3.3;vec2 id=floor(gg);vec2 f=fract(gg)-.5;
   float r=h21(id+floor(T*.35+h21(id)*3.)*7.);float life=fract(T*.35+h21(id)*3.);
   vec2 o=(h22(id+r)-.5)*.5;o.y+=life*life*.25;float rad=(.1+.22*r)*step(.45,r)*pov.x*(1.-life*.5);
   float l=length(f-o);
   if(l<rad){su-=(f-o)*.16*(1.-l/rad)/(1.+float(k)*.7);wetm=max(wetm,smoothstep(rad,rad*.6,l));}}}
 float eb=pov.w*smoothstep(.05,.5,r2)*.03;
 vec3 c;
 float ca=.006*r2*(1.+kick*1.5);
 if(fx.y>0.){c=vec3(0.);for(int i=0;i<8;i++){float k=1.-fx.y*.12*float(i)/8.;c+=scn(.5+(su-.5)*k,eb);}c/=8.;}
 else{c.r=scn(su-cc*ca,eb).r;c.g=scn(su,eb).g;c.b=scn(su+cc*ca,eb).b;}
 // bloom
 vec3 b=vec3(0.);float w=0.;
 for(int l=2;l<8;l++){float wl=1./(1.+float(l-2)*.35);
  vec2 px=exp2(float(l)+lod0)/textureSize(S,0)*.5;float L=float(l)+lod0;
  vec3 s=(textureLod(S,su+px*vec2(1,1),L).rgb+textureLod(S,su+px*vec2(-1,1),L).rgb+textureLod(S,su+px*vec2(1,-1),L).rgb+textureLod(S,su+px*vec2(-1,-1),L).rgb)*.25;
  if(trK!=0){vec3 s2=(textureLod(S2,su+px*vec2(1,1),L).rgb+textureLod(S2,su+px*vec2(-1,1),L).rgb+textureLod(S2,su+px*vec2(1,-1),L).rgb+textureLod(S2,su+px*vec2(-1,-1),L).rgb)*.25;
   s=mix(s,s2,trK==1?trX:step(.5,trX));}
  b+=max(s-.62,0.)*wl;w+=wl;}
 c+=b/w*1.5;
 c+=wetm*.03;
 c*=grade.x;
 c*=1.+flash*1.6;c+=flash*.22;
 c=1.-exp(-c*1.55);c=pow(c,vec3(1.12));
 float lum=dot(c,vec3(.3,.59,.11));
 c=mix(vec3(lum),c,1.12*grade.y*(1.-pov.z));
 c*=mix(vec3(1.),vec3(1.08,1.,.9),grade.z);
 c=mix(c,vec3(.82,.86,.92),grade.w);
 // lens snow
 if(pov.y>0.){vec2 g=su*vec2(7.,4.);vec2 id=floor(g);vec2 f=fract(g)-.5;float r=h21(id+floor(T*.5+h21(id)*2.));
  float life=fract(T*.5+h21(id)*2.);vec2 o=(h22(id+r)-.5)*.6;float rad=(.12+.3*r)*step(.4,r);
  float e=smoothstep(.02,.3,r2);
  if(rad>.01)c=mix(c,vec3(.93,.95,1.),smoothstep(rad,rad*.3,length(f-o)+.1*vn(su*40.))*smoothstep(.5,.4,max(abs(f.x),abs(f.y))+rad*.3)*pov.y*(1.-life)*e*.8);
  c=mix(c,vec3(.9,.93,1.),pov.y*smoothstep(.12,.42,r2+.06*vn(su*9.+T*.2))*.55);}
 // film look
 if(fx.z>0.){vec3 sep=vec3(lum*1.08,lum*.96,lum*.78);c=mix(c,sep,fx.z*.72);
  c*=1.-fx.z*.25*smoothstep(.1,.5,r2);
  float sc=step(.985,h21(vec2(floor(su.x*300.),floor(T*14.))))*.25;c+=sc*fx.z*h21(vec2(su.y*40.,T));
  c*=1.-fx.z*.08*h21(vec2(floor(T*18.),3.));
  c+=(h21(gl_FragCoord.xy*.5+fract(T)*311.)-.5)*.12*fx.z;}
 c*=1.-r2*(.85+fx.w);
 float g=h21(gl_FragCoord.xy+fract(T)*917.)-.5;
 c+=g*.035*(1.2-lum);
 c*=fade;
 float bar=R.y*(1.-(R.x/2.35)/R.y)*.5;
 c*=step(bar,gl_FragCoord.y)*step(gl_FragCoord.y,R.y-bar);
 vec4 tx=texture(TX,uv);
 c=c*(1.-tx.a)+tx.rgb;
 O=vec4(clamp(c,0.,1.),1.);}
