uniform vec2 R; uniform float T;
uniform vec3 ro,cu,cv,cw; uniform float fl;
uniform int stage,sets;
uniform vec3 sunD,sunC,skT,skM,skH,fogC;
uniform float fogD,fogH,starA,domeA,clY,clA,rainA,snowA,wet,snowL,mistA,amb,orb,winA,strm,stY,ntBlur,tmaxS,clCov;
uniform vec4 ltn,glow,lone;
uniform vec4 chP[8],chR[8],chC[8],chF[8]; uniform int nCh;
uniform vec4 itP[12],itD[12],itC[12]; uniform int nIt;
uniform vec3 ntP[6],ntU[6],ntV[6]; uniform vec4 ntS[6]; uniform int nNt;
uniform sampler2D AT;
uniform vec4 pl0,pl0c,sp0,sp0d,sp0c;
uniform vec4 setA,setB,rkO; uniform vec3 stO;
uniform vec4 part,partC;
uniform float kick,bph,beatN;
out vec4 O;
vec2 gp;
float smin(float a,float b,float k){float h=clamp(.5+.5*(b-a)/k,0.,1.);return mix(b,a,h)-k*h*(1.-h);}
float sdRB(vec3 p,vec3 b,float r){vec3 q=abs(p)-b+r;return length(max(q,0.))+min(max(q.x,max(q.y,q.z)),0.)-r;}
float sdCap(vec3 p,vec3 a,vec3 b,float r){vec3 pa=p-a,ba=b-a;return length(pa-ba*clamp(dot(pa,ba)/dot(ba,ba),0.,1.))-r;}

// ================= sky =================
float bolt(vec2 p,float sd){float x=(fbm(vec2(p.y*2.5,sd))-.5)*.9+(fbm(vec2(p.y*12.,sd+3.))-.5)*.12+(h11(sd)-.5)*1.8;
 return exp(-abs(p.x-x)*90.)*smoothstep(-.2,.15,p.y);}
vec3 sky(vec3 rd,bool full){
 float y=rd.y;
 vec3 c=mix(skH,skM,smoothstep(0.,.3,y));c=mix(c,skT,smoothstep(.2,.9,y));
 c=mix(c,skH*.7,smoothstep(0.,-.4,y));
 float sd=max(dot(rd,sunD),0.);
 c+=sunC*(pow(sd,6.)*.25+pow(sd,60.)*.5);
 if(full){
  c+=sunC*smoothstep(.9991,.9996,sd)*5.;
  if(starA>.5&&rainA<.5){c+=vec3(.9,.94,1.)*(smoothstep(.9993,.9996,sd)*2.5*(.75+.25*fbm(rd.xy*90.))+pow(sd,300.)*.25);}
  if(starA>0.&&y>-.05){
   vec2 sp=vec2(atan(rd.z,rd.x),asin(clamp(y,-1.,1.)));
   for(int k=0;k<2;k++){vec2 g=sp*(60.+float(k)*45.)+float(k)*13.;vec2 id=floor(g);vec2 f=fract(g)-.5;float r=h21(id);vec2 o=(h22(id+3.)-.5)*.7;
    c+=starA*smoothstep(.09,.0,length(f-o))*step(.7,r)*(.55+.45*sin(T*3.+r*50.))*vec3(.9,.95,1.)*(1.2-.5*float(k))*smoothstep(-.05,.2,y);}
   float band=exp(-pow((rd.x*.6+rd.y*.5-rd.z*.62)*2.6,2.));
   c+=starA*band*(vec3(.16,.2,.36)*fbm(sp*5.)+vec3(.3,.2,.3)*pow(fbm(sp*9.+4.),3.))*.9;}
  if(domeA>0.&&y>0.){vec2 uu=rd.xz/(y+.2)*.6+vec2(0.,T*.02);float cl=smoothstep(.42,.85,fbm(uu*1.5+7.));
   c=mix(c,skH*.85+sunC*.3*(.3+sd),cl*domeA*smoothstep(0.,.25,y));}
  if(ltn.x>0.)c+=ltn.x*vec3(.6,.75,1.)*(.22+bolt(gp+vec2(ltn.z,-.1),ltn.y)*3.);
 }
 return c;}

// ================= SDF world =================
float gd;int gm;int gi;vec3 gl;
void U(float d,int m){if(d<gd){gd=d;gm=m;}}

void mapStatue(vec3 p){
 vec3 q=p-vec3(0.,stY,0.);
 float bd=length(q-vec3(0.,.9,-.1))-1.3; if(bd>.4){U(bd,0);return;}
 float d=sdRB(q-vec3(0.,.17,0.),vec3(.36,.19,.36),.03);
 d=min(d,sdRB(q-vec3(0.,.02,0.),vec3(.52,.04,.52),.02));
 vec3 a=vec3(abs(q.x),q.y,q.z);
 float b=sdCap(q,vec3(0.,.56,.02),vec3(0.,.9,.0),.112);
 b=smin(b,length(q-vec3(0.,.93,-.015))-.145,.09);
 b=smin(b,sdRB(q-vec3(0.,.33,-.2),vec3(.205,.175,.24),.13),.1);
 b=smin(b,sdRB(q-vec3(0.,.2,-.4),vec3(.2,.2,.07),.07),.09);
 b=smin(b,sdCap(a,vec3(.0,1.0,0.),vec3(.19,1.0,0.),.068),.06);
 b=smin(b,sdCap(q,vec3(0.,1.04,0.),vec3(0.,1.14,-.01),.046),.03);
 b=smin(b,length(q-vec3(0.,1.225,-.02))-.1,.02);
 b=smin(b,length(q-vec3(0.,1.3,.07))-.058,.04);
 b=smin(b,sdCap(q,vec3(0.,1.2,.085),vec3(0.,.72,.17),.07),.07);
 b=smin(b,sdCap(a,vec3(.2,1.0,0.),vec3(.29,1.27,-.13),.045),.04);
 b=smin(b,sdCap(a,vec3(.29,1.27,-.13),vec3(.13,1.5,-.24),.036),.03);
 b=smin(b,length(a-vec3(.11,1.54,-.24))-.046,.03);
 b+=.0022*sin(q.y*40.+2.*sin(q.x*12.+q.z*7.))*smoothstep(.8,.35,q.y)*smoothstep(.04,.2,q.y);
 d=min(d,sdRB(q-vec3(0.,.085,0.),vec3(.44,.035,.44),.012));
 d=min(d,sdRB(q-vec3(0.,.345,0.),vec3(.385,.02,.385),.012));
 U(min(d,b),5);
 U(length(q-vec3(0.,1.66,-.24))-.14,6);}

void mapCampus(vec3 p){
 float bx=max(max(abs(p.x)-5.2,max(2.-p.z,p.z-7.2)),p.y-1.2);
 if(bx>.5){U(bx,0);return;}
 vec2 id=floor(p.xz/.8);vec2 f=p.xz-(id+.5)*.8;float h=h21(id+3.),h2=h21(id+11.);
 float lim=min(.4-abs(f.x),.4-abs(f.y))+.07;
 if(abs(id.x+.5)<.6){U(lim,0);return;}
 if(h>.82){ // plaza with trees
  float d=length(vec3(f.x,p.y-.26,f.y))-.11;
  d=min(d,length(vec3(f.x-.16,p.y-.2,f.y+.12))-.08);
  d=min(d,length(vec3(f.x+.14,p.y-.21,f.y-.15))-.085);
  if(d<gd){gd=d;gm=8;gl=vec3(h2);}
  U(lim,0);return;}
 float hg=.16+.34*h*h;
 vec3 q=vec3(f.x,p.y-.05-hg*.5,f.y);
 float d=sdRB(q,vec3(.2+.11*h2,hg*.5+.06,.15+.12*fract(h2*7.)),.012);
 if(d<gd){gd=d;gm=7;gl=vec3(h,h2,0.);}
 U(lim,0);}

float hStep(float s){return .064*clamp(floor((s-.3)/.12)+1.,0.,15.);}
float flightD(vec3 q){
 float s=q.z;float i0=clamp(floor((s-.3)/.12),0.,14.);float d2=q.y;
 for(int j=-1;j<=1;j++){float i=clamp(i0+float(j),0.,14.);d2=min(d2,max(.3+.12*i-s,q.y-.064*(i+1.)));}
 float d=max(d2,max(abs(q.x)-.3,max(-s-.3,s-2.7)));
 d=max(d,(clamp((s-.3)/1.8,0.,1.)*.96-.4)-q.y);
 float sl=clamp((s-.3)/1.8,0.,1.)*.96;
 float wl=max(max(abs(abs(q.x)-.335)-.035,q.y-sl-.085),max(sl-.4-q.y,max(-s-.3,s-2.7)));
 return min(d,wl);}
void mapStairs(vec3 p){
 vec3 l=vec3(p.z-stO.z,p.y-stO.y,p.x-stO.x);
 float k=floor((l.x+l.z+.3)/4.8);float d=1e5;
 if(setA.w>.5){d=flightD(l);d=min(d,sdRB(l-vec3(0.,.76,2.75),vec3(.55,.2,.55),.02));}
 else for(int j=-1;j<=1;j++){vec3 q=l-(k+float(j))*vec3(2.4,1.92,2.4);
  d=min(d,flightD(q));d=min(d,flightD(vec3(q.z-2.4,q.y-.96,q.x)));}
 if(d<gd){gd=d;gm=14;gl=l;}}

void mapRocks(vec3 p){
 float bd=length(p-rkO.xyz-vec3(0.,0.,rkO.w*.17))-1.2;
 if(bd>.5){U(bd,0);}
 else for(int i=0;i<9;i++){float fi=float(i)+floor(rkO.w)-3.;float h=h11(fi*1.7+2.);
  vec3 c=rkO.xyz+vec3((h-.5)*.05+(mod(fi,2.)-.5)*.09,0.,fi*.17);
  float fall=max(rkO.w-fi-.7,0.);
  c.y-=fall*fall*.3;c.x+=fall*(h-.5)*.25;
  vec3 q=p-c;q.xz=rot(fi*2.+fall*(h-.5)*2.)*q.xz;q.xy=rot(fall*.5*(h-.5)*3.)*q.xy;
  float sep=min(fall,1.5)*.035;
  q.x=abs(q.x)-.038-sep;q.y+=sep*.6*sign(q.z);
  float d=sdRB(q,vec3(.037,.032,.068),.022)+(vn(q.xz*50.+fi)-.5)*.006;
  U(d*.8,15);}
 if(setB.w>.5){vec3 q=p-setB.xyz;float tw=1.+q.y*.25;
  float d=sdRB(q+vec3(0.,.75,0.),vec3(.14*tw,.75,.13*tw),.07)+(vn(q.xy*14.)+vn(q.zy*14.)-1.)*.02;
  U(d*.7,15);}}

void mapDesk(vec3 p){
 U(p.y,11);
 float n=setA.x;
 if(n>0.){float bb=sdRB(p-vec3(0.,.5,0.),vec3(.64,.55,.48),.0);
  if(bb>.3)U(bb,0);
  else for(int i=0;i<10;i++){float fi=float(i);if(fi>=n)break;
   float a=clamp(n-fi,0.,1.);float yo=(1.-a)*(1.-a)*.9;
   vec3 c=vec3((h11(fi*3.1)-.5)*.05,.035+fi*.07+yo,(h11(fi*5.3)-.5)*.04);
   vec3 q=p-c;q.xz=rot((h11(fi*7.7)-.5)*.3)*q.xz;
   float d=sdRB(q,vec3(.52-.047*fi,.031,.36-.03*fi),.006);
   if(d<gd){gd=d;gm=12;gi=i;gl=q;}}}
 if(setA.y>.5){vec3 L0=vec3(.95,0.,-.35),J=vec3(1.02,.62,-.42),H=vec3(.64,.88,-.24);
  float bd=length(p-vec3(.85,.45,-.33))-.6;
  if(bd>.3)U(bd,0);
  else{
   float d=max(length(p.xz-L0.xz)-.13,abs(p.y-.012)-.012);
   d=min(d,sdCap(p,L0+vec3(0.,.02,0.),J,.014));d=min(d,sdCap(p,J,H,.014));
   vec3 hd=normalize(vec3(-.55,-.75,.3));
   float tc=clamp(dot(p-H,hd)/.13,0.,1.);
   d=min(d,abs(length(p-H-hd*.13*tc)-mix(.025,.085,tc))-.006);
   U(d*.8,13);
   U(length(p-H-hd*.09)-.035,25);}}}

float sdChar(vec3 p,int i){
 vec4 P=chP[i],Rr=chR[i],C=chC[i],F=chF[i];
 vec3 q=(p-P.xyz)/P.w;
 float bd=length(q-vec3(0.,.55,0.))-1.05;if(bd>.3){U(bd*P.w,0);return bd*P.w;}
 float cy=cos(Rr.x),sy=sin(Rr.x);q.xz=vec2(cy*q.x-sy*q.z,sy*q.x+cy*q.z);
 float ph=Rr.y,sit=C.w;
 float bob=.04*abs(sin(ph));
 vec3 b=q-vec3(0.,.56+bob-.16*sit,0.);
 b.xy=rot(.09*sin(ph))*b.xy;b.yz=rot(Rr.z)*b.yz;
 float d=sdRB(b,vec3(.30,.27,.23),.13);int m=2;
 float sx=sign(q.x),sw=.14*sin(ph);
 vec3 ql=vec3(abs(q.x),q.y,q.z);
 d=min(d,sdCap(ql,vec3(.14,.34-.16*sit,0.),mix(vec3(.14,.05+.05*max(sx*sin(ph),0.),sx*sw),vec3(.15,.2,.36),sit),.075));
 vec3 bl=vec3(abs(b.x),b.y,b.z);float sb=sign(b.x);
 vec3 ab=vec3(.43,-.2,-sb*sw*1.2);
 float au=Rr.w;
 if(au>0.)ab=mix(ab,vec3(.47,.44,.06),min(au,1.));
 else ab=mix(ab,vec3(.22,.0,.46),min(-au,1.));
 d=min(d,sdCap(bl,vec3(.33,.04,0.),ab,.065));
 if(F.z>-.5){float dp=sdRB(b-vec3(0.,.02,-.3),vec3(.2,.2,.08),.06);if(dp<d){d=dp;m=4;}}
 if(F.y>.5){float dh=min(sdRB(b-vec3(0.,.38,0.),vec3(.31,.012,.31),.01),sdRB(b-vec3(0.,.32,0.),vec3(.17,.05,.17),.03));if(dh<d){d=dh;m=18;}}
 if(F.z>.5){float dm=1e5;for(int k=0;k<5;k++){float fk=float(k);
   dm=min(dm,length(b-vec3(-.2+.1*fk,-.02+.1*sin(fk*2.3)-.03*abs(sin(ph+fk)),-.42-.03*mod(fk,2.)))-.065*min(F.z,1.));}
  if(dm<d){d=dm;m=19;}}
 d*=P.w;
 if(d<gd){gd=d;gm=m;gi=i;gl=b;}
 return d;}

float sdPlane(vec3 q){
 q.x=abs(q.x);
 float tz=clamp(.5-q.z,0.,1.);float w=.34*tz;
 float yw=.015+.36*q.x;
 float dw=max(max(abs(q.y-yw)-.007,q.x-w),max(abs(q.z)-.5,.028-q.x));
 float dk=max(max(q.x-.026,-q.y-.15*tz),max(q.y-.04,abs(q.z)-.5));
 return min(dw,dk)*.7;}
float sdItem(vec3 p,int i){
 vec4 P=itP[i],D=itD[i];int ty=int(itC[i].a+.5);
 vec3 d=p-P.xyz;float bs=length(d)-P.w*(ty==12?2.7:.95);if(bs>P.w*.4)return bs;
 vec3 f=normalize(D.xyz),r=normalize(cross(vec3(0.,1.,0.),f)),u=cross(f,r);
 float cr=cos(D.w),sr=sin(D.w);vec3 r2=r*cr+u*sr,u2=u*cr-r*sr;
 vec3 q=vec3(dot(d,r2),dot(d,u2),dot(d,f))/P.w;
 float s=1e5;int m=20;
 if(ty==0){s=sdPlane(q);m=9;}
 else if(ty==1){s=min(sdRB(q,vec3(.45,.02,.45),.01),sdRB(q+vec3(0.,.11,0.),vec3(.25,.09,.25),.05));m=18;}
 else if(ty==2){s=max(length(q.xy)-.42,abs(q.z)-.06);m=19;}
 else if(ty==3){s=sdRB(q,vec3(.3,.42,.17),.06);vec3 a=vec3(abs(q.x),q.y,q.z);
  s=min(s,sdCap(a,vec3(.16,.42,0.),vec3(.16,.74,0.),.025));s=min(s,sdCap(q,vec3(-.16,.74,0.),vec3(.16,.74,0.),.03));
  s=min(s,length(vec3(a.x-.22,q.y+.45,q.z))-.06);}
 else if(ty==4){s=sdRB(q,vec3(.45,.22,.012),.01);m=19;}
 else if(ty==5){vec2 e=q.xy;float bd=smin(length(e-vec2(0.,-.22))-.27,length(e-vec2(0.,.1))-.19,.08);
  s=max(bd,abs(q.z)-.07);s=min(s,sdRB(q-vec3(0.,.5,.03),vec3(.035,.3,.03),.01));s=min(s,sdRB(q-vec3(0.,.84,.03),vec3(.06,.07,.03),.01));m=22;}
 else if(ty==6){s=length(q)-.45;m=23;}
 else if(ty==7){s=sdRB(q,vec3(.27,.5,.035),.04);m=21;}
 else if(ty==8){s=sdCap(q,vec3(0.,0.,-.5),vec3(0.,0.,.42),.05);}
 else if(ty==9){s=max(sdRB(q,vec3(.42,.64,.07),.02),-sdRB(q,vec3(.31,.55,.2),.0));m=16;
  float g=sdRB(q,vec3(.31,.55,.006),.0);if(g<s){s=g;m=17;}}
 else if(ty==10){s=sdRB(q,vec3(.3,.26,.36),.22);}
 else if(ty==11){s=sdRB(q,vec3(.42,.42,.13),.03);m=24;}
 else if(ty==12){s=smin(sdRB(q,vec3(.3,.26,.36),.22),sdCap(q,vec3(0.,-.15,-.25),vec3(0.,-1.5,-1.9),.2),.2);}
 s*=P.w;
 if(s<gd){gd=s;gm=m;gi=i;gl=q;}
 return s;}

void mapNotes(vec3 p){
 for(int i=0;i<nNt;i++){vec3 d=p-ntP[i];vec3 Uu=ntU[i],Vv=ntV[i];float lu=length(Uu),lv=length(Vv);
  vec3 n=normalize(cross(Vv,Uu));
  float a=dot(d,Uu)/lu,b=dot(d,Vv)/lv,c=dot(d,n)-ntS[i].w*abs(a);
  vec3 q=vec3(abs(a)-lu,abs(b)-lv,abs(c)-lu*.006);
  float dd=(length(max(q,0.))+min(max(q.x,max(q.y,q.z)),0.))*.8;
  if(dd<gd){gd=dd;gm=10;gi=i;gl=vec3(a/lu,b/lv,c);}}}

float map(vec3 p){
 gd=1e5;gm=0;
 if((sets&1)!=0){mapStatue(p);mapCampus(p);}
 if((sets&2)!=0)mapStairs(p);
 if((sets&4)!=0)mapRocks(p);
 if((sets&8)!=0)mapDesk(p);
 for(int i=0;i<nCh;i++)sdChar(p,i);
 for(int i=0;i<nIt;i++)U(sdItem(p,i),gm);
 if(nNt>0)mapNotes(p);
 return gd;}
vec3 nrm(vec3 p,float e){vec2 k=vec2(1.,-1.);
 return normalize(k.xyy*map(p+k.xyy*e)+k.yyx*map(p+k.yyx*e)+k.yxy*map(p+k.yxy*e)+k.xxx*map(p+k.xxx*e));}
float sdfSh(vec3 q,vec3 L,float mx){float sh=1.,t=.012;
 for(int i=0;i<22;i++){float d=map(q+L*t);sh=min(sh,9.*d/t);if(sh<.02)break;t+=clamp(d,.01,.25);if(t>mx)break;}
 return clamp(sh,0.,1.);}
float sdfAO(vec3 q,vec3 n){float a=0.,s=1.;for(int i=1;i<=4;i++){float h=.012+.035*float(i);a+=(h-map(q+n*h))*s;s*=.7;}
 return clamp(1.-4.*a,0.,1.);}
float terSh(vec3 q){float sh=1.,st=.06;
 for(int i=0;i<16;i++){vec3 s=q+sunD*st;float dh=s.y-terH(s.xz,4);sh=min(sh,9.*dh/st);if(sh<.02)break;st+=max(dh*.7,.07);if(st>10.)break;}
 return clamp(sh,0.,1.);}

vec3 lit(vec3 q,vec3 n,vec3 rd,vec3 alb,float spec,float tt){
 float sh=1.,ao=1.;
 if(stage==0&&dot(n,sunD)>0.)sh=terSh(q+n*.012);
 float sdn=map(q+n*.03);
 if(sdn<1.2){if(sh>.02&&dot(n,sunD)>0.)sh=min(sh,sdfSh(q+n*.004,sunD,1.6));ao=sdfAO(q,n);}
 float dif=max(dot(n,sunD),0.);
 vec3 c=alb*(sunC*dif*sh*1.5+mix(skM,skT,.4)*(.5+.5*n.y)*amb*ao+skH*.14*max(dot(n,-sunD*vec3(1.,0.,1.)),0.)*ao);
 vec3 rf=reflect(rd,n);
 c+=sunC*spec*pow(max(dot(rf,sunD),0.),24.)*sh;
 c+=alb*skH*.22*pow(1.-max(dot(n,-rd),0.),3.)*ao*amb;
 if(pl0c.a>0.){vec3 L=pl0.xyz-q;float dl=length(L);L/=dl;float at=1./(1.+dl*dl*pl0.w);
  float s2=(pl0c.a>1.5&&sdn<1.5)?sdfSh(q+n*.004,L,dl):1.;
  c+=(alb*max(dot(n,L),0.)+spec*pow(max(dot(rf,L),0.),24.))*pl0c.rgb*at*s2*mix(1.,ao,.5);}
 if(sp0c.a>0.){vec3 L=sp0.xyz-q;float dl=length(L);L/=dl;float cone=smoothstep(sp0.w,sp0.w+sp0d.w,dot(-L,sp0d.xyz));
  c+=alb*sp0c.rgb*max(dot(n,L),0.)*cone*sdfSh(q+n*.004,L,dl);}
 c+=alb*ltn.x*vec3(.6,.75,1.)*(.35+.65*max(n.y,0.))*1.3;
 return c;}

// ================= terrain =================
float marchTer(vec3 o,vec3 rd,float tmax){
 float tt=.03;
 if(o.y>17.5){if(rd.y>=0.)return -1.;tt=(o.y-17.5)/-rd.y;}
 for(int i=0;i<150;i++){vec3 q=o+rd*tt;float dh=q.y-terH(q.xz,6);if(dh<.0012*tt)return tt;tt+=dh*.38+.0015*tt;if(tt>tmax||(q.y>17.5&&rd.y>0.))break;}
 return -1.;}
vec3 shadeTer(vec3 q,vec3 rd,float tt){
 float ep=.0025*tt+.0015;
 int no=tt<5.?6:tt<12.?7:9;
 float h0=terH(q.xz,no);
 vec3 n=normalize(vec3(h0-terH(q.xz+vec2(ep,0.),no),ep,h0-terH(q.xz+vec2(0.,ep),no)));
 float tx=fbm(q.xz*3.+q.y*2.),tx2=fbm(q.xz*17.);
 if(tt<8.){float bx=fbm(q.xz*70.);n=normalize(n+vec3(bx-.5,0.,fbm(q.xz*70.+9.)-.5)*.16*smoothstep(8.,2.,tt)*(snowL<-1.?.4:1.));tx2=mix(tx2,bx,.4);}
 vec3 rock=mix(vec3(.15,.13,.13),vec3(.42,.34,.28),tx)*(.8+.4*tx2);
 vec3 grass=mix(vec3(.12,.24,.07),vec3(.34,.4,.12),tx2);
 float gr=smoothstep(.6,.85,n.y+(tx-.5)*.3)*smoothstep(6.,2.5,q.y+(tx-.5)*2.5);
 vec3 alb=mix(rock,grass,gr);
 if(tt<60.&&gr>.05){ // miniature forest
  vec2 g=q.xz*7.;vec2 id=floor(g);float r=h21(id+5.);vec2 o=(h22(id+1.)-.5)*.5;vec2 fd=fract(g)-.5-o;float rad=.2+.2*r;float l=length(fd);
  float tm=step(.45,r)*smoothstep(rad,rad*.75,l)*smoothstep(.2,.5,gr)*smoothstep(60.,30.,tt)*smoothstep(2.5,6.,tt)*smoothstep(.25,.6,q.y)*smoothstep(5.,3.,q.y);
  if(tm>0.){alb=mix(alb,mix(vec3(.05,.17,.06),vec3(.17,.33,.09),r)*(.7+.5*fbm(q.xz*60.)+.55*sqrt(max(1.-l*l/(rad*rad),0.))),tm);n=normalize(mix(n,normalize(vec3(fd.x,sqrt(max(rad*rad-l*l,0.))+.02,fd.y)),tm*.8));}
  vec2 gs=(q.xz+normalize(sunD.xz+1e-4)*.05)*7.;vec2 is=floor(gs);float rs=h21(is+5.);float rds=.2+.2*rs;
  float ts=step(.45,rs)*smoothstep(rds,rds*.5,length(fract(gs)-.5-(h22(is+1.)-.5)*.5))*smoothstep(.2,.5,gr)*smoothstep(60.,30.,tt)*smoothstep(2.5,6.,tt)*smoothstep(.25,.6,q.y)*smoothstep(5.,3.,q.y);
  alb*=1.-.5*ts*(1.-tm);
 }
 if(tt<10.){vec2 g=q.xz*85.;vec2 id=floor(g);float r=h21(id);float d2=length(fract(g)-.5-(h22(id+2.)-.5)*.6);
  float dt=smoothstep(.2,.1,d2)*step(.93,r)*smoothstep(10.,4.,tt);
  alb=mix(alb,r>.95?vec3(.95,.9,.55):r>.9?vec3(.92,.6,.65):vec3(.5,.47,.42),dt*smoothstep(.2,.6,gr+.2));
  alb*=.86+.28*vn(q.xz*230.)*smoothstep(8.,1.,tt)+.14*(1.-smoothstep(8.,1.,tt));}
 alb=mix(alb,vec3(.66,.58,.42)*(.85+.3*tx2),smoothstep(.075,.02,q.y+(tx2-.5)*.03));
 float cz=smoothstep(.3,0.,max(abs(q.x)-5.2,max(2.-q.z,q.z-7.2)));
 alb=mix(alb,vec3(.5,.48,.45)*(.8+.4*tx2),cz*.4);
 vec3 emi=vec3(0.);
 if(cz>0.){vec2 cf=fract(q.xz/.8);vec2 cb=min(cf,1.-cf)*.8;float rdm=smoothstep(.075,.055,min(cb.x,cb.y));
  alb=mix(alb,vec3(.2,.2,.22),rdm*cz);alb=mix(alb,vec3(.8),rdm*cz*step(abs(min(cb.x,cb.y)-.0),.006)*step(.5,fract((cb.x<cb.y?q.z:q.x)*6.)));
  float ll=length(cb-vec2(.07));emi+=vec3(1.,.78,.45)*winA*cz*(exp(-ll*28.)*1.2+smoothstep(.012,.006,ll)*3.);}
 float sn=smoothstep(.45,.75,n.y+(tx-.5)*.3)*smoothstep(snowL,snowL+1.2,q.y+(tx-.5)*.9);
 float spec=wet*.5;
 if(q.z>-.3&&q.z<46.){
  float px=pathX(q.z);float dpx=(pathX(q.z+.04)-pathX(q.z-.04))/.08;
  float dp=abs(q.x-px)/sqrt(1.+dpx*dpx);
  float pm=smoothstep(.075,.045,dp+(tx2-.5)*.03)*smoothstep(-.3,.2,q.z)*smoothstep(46.,40.,q.z);
  alb=mix(alb,vec3(.66,.58,.44)*(.8+.4*tx2),pm*(1.-sn*.6));
  if(strm>0.){float fl2=fbm(vec2(dp*40.,q.z*9.+T*5.));alb=mix(alb,vec3(.25,.33,.42),pm*strm*.8);spec+=pm*strm*2.;emi+=vec3(.5,.6,.75)*pm*strm*.12*smoothstep(.45,.8,fl2);}
  vec3 warm=vec3(1.,.66,.28);
  if(glow.x>0.)emi+=warm*glow.x*(smoothstep(.1,.03,dp)*1.6+exp(-dp*7.)*.3)*smoothstep(glow.w+.5,glow.w-.5,q.z);
  if(glow.z>0.){float cell=q.z*2.6-T*.5;float dz=abs(fract(cell)-.5)/2.6;float l=length(vec2(dp,dz*1.5));
   float on=step(.25,h11(floor(cell)+floor(T*.5+.0)*0.));
   emi+=vec3(1.,.82,.55)*glow.z*on*(smoothstep(.035,.012,l)*5.+exp(-l*22.)*.8)*smoothstep(9.,11.,q.z);}
  if(glow.y>0.){for(int k=0;k<10;k++){float fk=float(k);if(fk>=glow.y)break;float zk=9.+12.*(.25+.5*fk)/5.;
    float l=length(q.xz-vec2(pathX(zk),zk));float a=clamp(glow.y-fk,0.,1.);
    emi+=warm*a*(smoothstep(.07,.03,l)*5.+exp(-l*9.)*.9);}}}
 alb=mix(alb,vec3(.86,.89,.95),sn);spec+=sn*.35;
 if(wet>0.)alb*=mix(1.,.6,wet);
 vec3 c=lit(q,n,rd,alb,spec,tt)+emi;
 return c;}

// ================= materials =================
vec3 atlas(float cell,vec2 uv,float lod){float cx=mod(cell,4.),cy=floor(cell/4.);
 uv=clamp(uv,.004,.996);return textureLod(AT,vec2((cx+uv.x)/4.,(cy+1.-uv.y)/8.),lod).rgb;}
vec3 shadeObj(vec3 q,vec3 rd,float tt,int m,int id,vec3 l){
 vec3 n=nrm(q,.0005+.0006*tt);
 vec3 alb=vec3(.5),emi=vec3(0.);float spec=.08;
 if(m==2){vec4 C=chC[id],F=chF[id];alb=C.rgb*(.92+.16*vn(l.xy*9.+l.z*7.));
  if(l.z>.12){vec2 e=vec2(abs(l.x)-.115,l.y-.07);float k;
   bool blk=fract(T*.19+float(id)*.37)<.028;
   if(F.x<.5&&!blk)k=smoothstep(.052,.044,length(e));
   else if(F.x<1.5)k=smoothstep(.02,.012,abs(e.y))*step(abs(e.x),.055);
   else k=smoothstep(.018,.01,abs(length(e+vec2(0.,.03))-.05))*step(-.02,e.y);
   alb=mix(alb,vec3(.02),k);
   if(F.x<.5&&!blk)alb+=vec3(.9)*smoothstep(.016,.008,length(e-vec2(.015*sign(l.x),.018)));
   alb=mix(alb,vec3(1.,.5,.42),.4*smoothstep(.06,.03,length(vec2(abs(l.x)-.2,l.y+.015))));}
  if(F.w>0.&&l.z>0.){float hl=length(l.xy-vec2(0.,-.1));emi+=vec3(1.,.55,.25)*F.w*(exp(-hl*9.)*1.6+smoothstep(.07,.03,hl)*2.);}
  emi+=alb*(sunC*.4+skH*.15)*pow(1.-max(dot(n,-rd),0.),2.5)*max(dot(n,sunD)*.5+.5,0.);
  emi+=alb*(skH*.2+sunC*.07+.012)*max(dot(n,-rd),0.);
  spec=.06;}
 else if(m==4){alb=mix(vec3(.2,.26,.4),chC[id].rgb*.5,.25);}
 else if(m==5){float w1=fbm(q.xy*9.+q.z*7.),w2=fbm(vec2(q.x*30.+q.z*30.,q.y*4.));
  alb=mix(vec3(.5,.48,.45),vec3(.74,.72,.67),w1)*(.78+.3*w2)*mix(.8,1.,smoothstep(stY,stY+.5,q.y));
  alb=mix(alb,vec3(.42,.47,.4),.25*smoothstep(.55,.75,fbm(q.xz*14.+q.y*5.)));spec=.2;}
 else if(m==6){float nv=max(dot(n,-rd),0.);alb=vec3(1.,.75,.3);emi=mix(vec3(1.,.36,.08),vec3(1.,.8,.42),pow(nv,1.4))*orb*(.3+.55*nv)*(.85+.3*fbm(n.xy*5.+n.z*3.+T*.1));spec=.6;}
 else if(m==7){vec3 w=mix(vec3(.82,.78,.72),vec3(.7,.5,.42),step(.5,l.y));w=mix(w,vec3(.72,.76,.8),step(.75,l.x));
  if(n.y>.5)alb=mix(vec3(.46,.22,.16),vec3(.3,.31,.34),step(.4,l.x))*(.8+.4*step(.5,fract(q.x*9.+q.z*9.)));
  else{float u=(abs(n.x)>.5?q.z:q.x)*13.,v=q.y*13.;float wn=step(.3,fract(u))*step(.35,fract(v))*step(.13,q.y);
   float on=step(.62,h21(floor(vec2(u,v))+l.xy*31.));
   alb=mix(w,vec3(.12,.16,.22),wn);emi=vec3(1.,.72,.38)*winA*wn*on*1.6;spec=wn*.4;}}
 else if(m==8){alb=mix(vec3(.12,.3,.1),vec3(.3,.42,.14),l.x)*(.8+.5*fbm(q.xz*40.));}
 else if(m==9){vec4 C=itC[id];alb=C.rgb;
  float bk=pow(max(dot(rd,sunD),0.),2.);emi=C.rgb*sunC*.35*bk+C.rgb*skH*.1;
  alb*=1.-.3*smoothstep(.014,.0,abs(abs(l.x)-.03))-.18*smoothstep(.01,.0,abs(abs(l.x)-.03-.17*clamp(.5-l.z,0.,1.)));
  alb*=mix(.72,1.,smoothstep(-.3,.4,n.y));
  spec=.1;}
 else if(m==10){vec4 S=ntS[id];float side=l.z>0.?S.x:S.y;vec2 uv=vec2(l.x*.5+.5,l.y*.5+.5);if(l.z<=0.)uv.x=1.-uv.x;
  vec3 pc=vec3(.93,.91,.86);
  if(side<-.5)alb=pc;else{alb=atlas(side,uv,ntBlur);if(uv.x>S.z)alb=pc;}
  alb*=.94+.1*fbm(uv*30.);emi=alb*sunC*.12*pow(max(dot(rd,sunD),0.),2.);}
 else if(m==11){float g=fbm(vec2(q.x*2.,q.z*40.));alb=mix(vec3(.32,.19,.1),vec3(.5,.32,.17),g)*(.85+.3*fbm(q.xz*9.));spec=.25;}
 else if(m==12){float fi=float(id);vec3 cv2=.5+.45*cos(6.2832*(h11(fi*1.3+.4)+vec3(0.,.33,.67)));cv2=mix(cv2,vec3(.6,.25,.2),.35);
  float hsx=.52-.047*fi,hsz=.36-.03*fi;
  bool page=abs(l.y)<.024&&(l.x>hsx-.01||abs(l.z)>hsz-.01);
  alb=page?vec3(.9,.87,.78)*(.8+.2*step(.5,fract(l.y*260.))):cv2;
  if(!page&&l.y>0.)alb=mix(alb,vec3(.9,.8,.5),step(abs(l.z+hsz*.45),.02)*step(abs(l.x),hsx*.6)*.8);
  spec=.15;}
 else if(m==13){alb=vec3(.1,.11,.13);spec=.7;}
 else if(m==25){alb=vec3(1.);emi=pl0c.rgb*1.5+vec3(.3,.25,.15);}
 else if(m==14){vec3 st=mix(vec3(.46,.44,.44),vec3(.62,.56,.5),fbm(l.xz*5.+l.y*3.))*(.7+.5*fbm(l.xz*14.+l.y*9.));
  st*=1.-.35*smoothstep(.012,.0,abs(fract(l.x/.2+floor(l.y/.064+.01)*.37+floor(l.z/.12)*.21)-.5));
  if(n.y>.5)st=mix(st,vec3(.2,.3,.12),.55*smoothstep(.5,.75,fbm(l.xz*9.+3.))*(1.-wet*.5));alb=st;spec=.1+wet*.5;
  if(setA.z>0.){float k=floor((l.x+l.z+.3)/4.8);vec3 e=l-k*vec3(2.4,1.92,2.4);float idx;float fr;
   if(abs(e.x)<.31&&e.z<2.71){idx=k*30.+floor((e.z-.3)/.12);fr=fract((e.z-.3)/.12);}
   else{idx=k*30.+15.+floor((e.x-.3)/.12);fr=fract((e.x-.3)/.12);}
   float on=smoothstep(setA.z+.5,setA.z-.5,idx);
   if(n.y<.5)emi=vec3(1.,.66,.3)*on*.55*smoothstep(.0,.03,fract(l.y/.064+.5)-.2);
   else emi=vec3(1.,.66,.3)*on*.1*exp(-fr*5.);}}
 else if(m==15){alb=mix(vec3(.3,.29,.3),vec3(.62,.6,.58),fbm(q.xz*20.+q.y*30.))*(.6+.6*smoothstep(-.3,.6,n.y));spec=.1;}
 else if(m==16){alb=vec3(.9,.7,.35);spec=.8;emi=vec3(1.,.7,.3)*.25;}
 else if(m==17){emi=vec3(1.,.82,.5)*(3.+kick);alb=vec3(1.);}
 else if(m==18){alb=vec3(.035,.04,.07);spec=.25;}
 else if(m==19){alb=vec3(1.,.72,.25);spec=1.2;emi=vec3(1.,.7,.25)*.12;}
 else if(m==20){alb=itC[id].rgb;}
 else if(m==21){alb=vec3(.03);spec=.8;if(l.z>0.&&abs(l.x)<.24&&abs(l.y)<.46){vec2 uv=vec2(l.x/.48+.5,l.y/.92+.5);
   emi=atlas(7.,uv,0.)*1.3*(.8+.2*sin(T*9.));}}
 else if(m==22){alb=mix(vec3(.65,.38,.16),vec3(.2,.1,.05),step(.38,l.y));if(l.y<.38)alb=mix(alb,vec3(.05),smoothstep(.09,.07,length(l.xy-vec2(0.,-.02))));spec=.5;}
 else if(m==23){alb=vec3(.85,.38,.1);float ln=min(min(abs(l.x),abs(l.y)),abs(abs(l.x)-.25+l.y*l.y*.6));alb=mix(vec3(.05),alb,smoothstep(.012,.022,ln));spec=.2;}
 else if(m==24){alb=l.y>.28?vec3(.75,.12,.1):vec3(.9,.88,.84);}
 if(m!=6&&m!=17&&m!=25&&m!=10){float sn=snowA*.0;alb=mix(alb,vec3(.9),sn);}
 if(wet>0.&&m!=10)spec+=wet*.4;
 return lit(q,n,rd,alb,spec,tt)+emi;}

vec3 water(vec3 q,vec3 rd,float tt){
 vec2 w=q.xz;float e=.02+.002*tt;
 float amp=.5/(1.+tt*.06);
 float h0=fbm(w*2.+vec2(T*.25,T*.1))+.5*fbm(w*7.-vec2(T*.3,0.));
 float hx=fbm((w+vec2(e,0.))*2.+vec2(T*.25,T*.1))+.5*fbm((w+vec2(e,0.))*7.-vec2(T*.3,0.));
 float hz=fbm((w+vec2(0.,e))*2.+vec2(T*.25,T*.1))+.5*fbm((w+vec2(0.,e))*7.-vec2(T*.3,0.));
 vec3 n=normalize(vec3(-(hx-h0)/e*.05*amp,1.,-(hz-h0)/e*.05*amp));
 vec3 rf=reflect(rd,n);rf.y=abs(rf.y);
 float fr=.03+.97*pow(1.-max(dot(n,-rd),0.),5.);
 vec3 deep=mix(skT,skM,.3)*.35+vec3(.0,.02,.03);
 float th=terH(q.xz,3);
 deep=mix(deep,vec3(.1,.32,.33)*(skH+.2),smoothstep(-.3,-.02,th)*.6);
 vec3 c=mix(deep,sky(rf,false),fr);
 float sd=max(dot(rf,sunD),0.);
 c+=sunC*(pow(sd,180.)*5.+pow(sd,30.)*.35);
 // orb reflection column
 if(orb>0.){vec3 ob=vec3(0.,stY+1.66,-.24);vec2 dd=q.xz-ob.xz;vec2 vd=normalize(ro.xz-ob.xz);
  float al=dot(dd,vd),pe=abs(dd.x*vd.y-dd.y*vd.x);
  if(al>0.)c+=vec3(1.,.7,.3)*orb*.5*exp(-pe*(3.+8./(1.+al)))*smoothstep(0.,.6,al)*exp(-al*.25)*(.5+.9*smoothstep(.4,.7,h0/1.5+n.x*4.));}
 float foam=smoothstep(-.06,.0,th+.03*sin(T*1.2+q.x*3.)+.02*h0);
 c=mix(c,vec3(.9,.92,.95)*(skH*.6+sunC*.3+.1),foam*.7);
 c+=ltn.x*vec3(.2,.25,.35)*.4;
 return c;}

float rainf(vec2 p,float t){float r=0.;for(int i=0;i<3;i++){float fi=float(i);
 vec2 g=vec2(p.x*(28.+fi*14.)+p.y*5.,p.y*(1.4+fi*.6)+t*(5.+fi*2.)+fi*7.);vec2 id=floor(g);float h=h21(id);vec2 f=fract(g);
 r+=step(.8,h)*smoothstep(.14,.0,abs(f.x-.5))*smoothstep(0.,.3,f.y)*smoothstep(1.,.6,f.y)*(.5-fi*.12);}return r;}
float snowf(vec2 p,float t){float s=0.;for(int i=0;i<5;i++){float fi=float(i);float sc=5.+fi*7.;
 vec2 g=p*sc+vec2(t*(2.2+fi*.8)+sin(t*.7+fi)*.6,t*(1.6+fi*.6))+fi*17.;vec2 id=floor(g);vec2 f=fract(g)-.5;vec2 o=(h22(id+fi*7.)-.5)*.7;float r=h21(id+3.+fi);
 s+=step(.55,r)*smoothstep(.14-fi*.02,.0,length(f-o))*(1.-fi*.15);}return s;}

vec3 parts(vec2 p){vec3 c=vec3(0.);int ty=int(part.w+.5);
 if(ty==1){for(int i=0;i<70;i++){float fi=float(i);float life=fract(T*.33+h11(fi));
   vec2 v0=vec2((h11(fi+7.)-.5)*1.3,.5+h11(fi+3.)*1.5);
   vec2 pos=part.xy+v0*life*1.2+vec2(.2*sin(T*2.+fi)*life,-.2*life*life);
   float l=length(p-pos);float tw=.5+.5*sin(T*20.+fi*7.);
   c+=partC.rgb*(exp(-l*110.)*2.4+exp(-l*22.)*.1)*(1.-life)*tw;}}
 else if(ty==2){for(int i=0;i<64;i++){float fi=float(i);float sp=.35+.4*h11(fi+1.);float y=1.15-fract(T*sp*.5+h11(fi+9.))*2.4;
   vec2 pos=vec2((h11(fi+4.)-.5)*4.4+.12*sin(T*1.5+fi),y);
   vec2 q=rot(T*(1.+h11(fi))*1.4+fi)*(p-pos);float sz=.012+.022*h11(fi+2.);
   float fv=abs(cos(T*3.*(h11(fi+5.)+.5)+fi));
   float m=smoothstep(.004,0.,max(abs(q.x)-sz*2.,abs(q.y)-sz*fv));
   c+=partC.rgb*m*(.35+.9*fv);}}
 else if(ty==3){vec2 d=p-part.xy;float l=length(d);float a=atan(d.y,d.x);
   c+=partC.rgb*(exp(-l*30.)*1.5+exp(-l*8.)*.25*(1.+.6*sin(a*8.+T*3.))+.5*exp(-abs(d.x)*90.)*exp(-abs(d.y)*9.)+.5*exp(-abs(d.y)*90.)*exp(-abs(d.x)*9.));}
 return c*part.z;}

// ================= space =================
vec3 cosmos(vec2 p){
 float pr=setA.x;
 vec3 c=vec3(.004,.006,.02);
 vec2 q=rot(T*.05)*p;
 float n1=fbm(q*1.3+vec2(T*.03,0.)),n2=fbm(q*2.6-vec2(0.,T*.04)+n1*2.);
 c+=(vec3(.25,.08,.4)*pow(n2,2.5)*1.3+vec3(.03,.25,.4)*pow(n1,3.)*1.5)*smoothstep(.2,.8,pr);
 float gz=smoothstep(.35,1.,pr);
 vec2 g=rot(.5)*p*vec2(1.,1.9)*mix(.25,1.4,gz);float r=length(g),a=atan(g.y,g.x);
 float arm=pow(.5+.5*cos(a*2.-log(r+.02)*4.5+T*.25),3.);
 float gal=exp(-r*2.2)*(.25+arm*1.2)*(.6+.8*fbm(g*9.+T*.05));
 c+=(mix(vec3(1.,.8,.55),vec3(.5,.65,1.),smoothstep(0.,.8,r))*gal*1.1+vec3(1.,.9,.7)*exp(-r*14.)*1.2)*gz;
 for(int l=0;l<5;l++){float f=fract(float(l)/5.-pr*.9-T*.03);float sc=mix(55.,5.,f);
  vec2 u=p*sc+float(l)*17.;vec2 id=floor(u);vec2 o=(h22(id)-.5)*.7;float rr=h21(id+9.);
  float s=smoothstep(.09,0.,length(fract(u)-.5-o))*step(.6,rr);
  c+=mix(vec3(.7,.8,1.),vec3(1.,.85,.7),rr)*s*smoothstep(0.,.2,f)*smoothstep(1.,.7,f)*(.5+kick*.5);}
 // earth
 float er=1.5*pow(1.-smoothstep(0.,.55,pr),2.2)+.004;float l=length(p);
 if(l<er){vec2 e=p/er;float z=sqrt(max(1.-dot(e,e),0.));vec3 n=vec3(e,z);
  vec2 sp=vec2(atan(n.x,n.z)+T*.02,asin(n.y));
  float ld=smoothstep(.5,.56,fbm(sp*2.5+3.));vec3 ec=mix(vec3(.02,.1,.3),vec3(.12,.25,.1),ld);
  float cl=smoothstep(.5,.75,fbm(sp*5.+T*.01));ec=mix(ec,vec3(.9),cl*.8);
  float df=max(dot(n,normalize(vec3(.7,.35,.5))),0.);
  vec3 night=vec3(1.,.7,.3)*ld*step(.75,h21(floor(sp*90.)))*.6*(1.-smoothstep(0.,.15,df));
  c=ec*(df*1.5+.02)+night+vec3(.3,.5,1.)*pow(1.-z,3.)*(df+.1)*1.5;}
 c+=vec3(.3,.5,1.)*exp(-max(l-er,0.)/er*14.)*.5*smoothstep(.6,.1,pr)*step(er,l);
 c+=vec3(.55,.75,1.)*exp(-l*l*900.)*smoothstep(.45,.6,pr)*1.5;
 return c;}

vec3 bgDesk(vec3 rd){
 vec3 c=mix(skH,skT,smoothstep(-.3,.7,rd.y));
 vec2 sp=vec2(atan(rd.x,rd.z)*2.,rd.y*3.);
 for(int k=0;k<2;k++){vec2 g=sp*(1.6+float(k))+float(k)*5.;vec2 id=floor(g);vec2 f=fract(g)-.5;float r=h21(id+2.);vec2 o=(h22(id)-.5)*.5;
  float l=length(f-o);float rad=.12+.14*r;
  c+=starA*mix(vec3(1.,.7,.35),vec3(.5,.7,1.),step(.7,r))*step(.45,r)*smoothstep(rad,rad*.8,l)*(.12+.2*smoothstep(rad*.6,rad,l));}
 c+=sunC*pow(max(dot(rd,sunD),0.),5.)*.5;
 return c;}

void main(){
 vec2 p=(gl_FragCoord.xy-.5*R)/R.y*2.;gp=p;
 if(stage==2){O=vec4(cosmos(p)+parts(p),1e3);return;}
 vec3 rd=normalize(p.x*cu+p.y*cv+fl*cw);
 float sd=max(dot(rd,sunD),0.);
 // --- objects
 float tS=-1.,t=.02;int hm=0,hi=0;vec3 hl=vec3(0.);
 for(int i=0;i<110;i++){float d=map(ro+rd*t);if(d<.0005*t+.00025){tS=t;hm=gm;hi=gi;hl=gl;break;}t+=d*.9;if(t>tmaxS)break;}
 if(tS>0.&&hm==0)tS=-1.;
 float tH=tS>0.?tS:1e3;int kind=tS>0.?1:0;
 vec3 c;
 if(stage==0){
  float tW=rd.y<0.?-ro.y/rd.y:1e3;
  float tT=marchTer(ro,rd,min(min(tH,tW+.5),170.));
  if(tT>0.&&tT<tH){tH=tT;kind=2;}
  if(tW<tH){tH=tW;kind=3;}
 }
 if(kind==0){c=stage==1?bgDesk(rd):sky(rd,true);}
 else{vec3 q=ro+rd*tH;
  if(kind==1)c=shadeObj(q,rd,tH,hm,hi,hl);
  else if(kind==2)c=shadeTer(q,rd,tH);
  else c=water(q,rd,tH);}
 // desk: overhead screen
 if(stage==1&&setB.x>.5&&rd.y>0.){float tp=(setB.y-ro.y)/rd.y;
  if(tp>0.&&tp<tH){vec3 q=ro+rd*tp;vec2 uv=q.xz*vec2(1.1,2.)+vec2(T*.22,0.);vec2 id=floor(uv);
   uv.x+=h11(id.y)*3.+T*.12*(h11(id.y+4.)-.3);id=floor(uv);vec2 f=fract(uv);
   float cell=8.+floor(h21(id+1.)*8.);
   vec3 tx=atlas(cell,(vec2(1.-f.x,f.y)-vec2(.06,.12))/vec2(.88,.76),0.);
   float in_=step(.06,f.x)*step(f.x,.94)*step(.12,f.y)*step(f.y,.88);
   float tw=.55+.45*sin(T*2.+h21(id)*30.);
   vec3 sc=vec3(.02,.04,.1)+tx*in_*tw*2.2*mix(vec3(.6,.8,1.),vec3(1.,.8,.5),h21(id+7.));
   sc*=exp(-length(q.xz)*.12);sc=mix(sc,vec3(.5,.74,1.)*1.15+vec3(.5)*exp(-length(q.xz)*1.5),clamp(setB.z*.5,0.,1.));
   c=sc;tH=tp;kind=4;}}
 // --- atmosphere
 vec3 fogc=mix(fogC,sunC*.8+fogC*.4,pow(sd,5.)*.55);
 if(stage==0){
  float td=min(tH,300.);
  float b=fogH;float fa=fogD*exp(-max(ro.y,0.)*b)*(abs(rd.y)>1e-4?(1.-exp(-td*rd.y*b))/(rd.y*b):td);
  float fg=1.-exp(-max(fa,0.));
  if(kind==0)fg*=smoothstep(.25,-.02,rd.y)*.9+(1.-exp(-fogD*3.))*.0;
  if(kind==3)fg=max(fg,1.-exp(-tH*.012));
  c=mix(c,fogc,clamp(fg,0.,1.));
  if(clA>0.&&abs(rd.y)>1e-4){for(int i=0;i<7;i++){float py=clY-float(i)*.085;float tc=(py-ro.y)/rd.y;
    if(tc>0.&&tc<tH){vec3 q=ro+rd*tc;
     float f=fbm(q.xz*(.3+clCov*1.1)+vec2(float(i)*3.,T*.05))+.25*fbm(q.xz*(1.4+clCov*3.)-T*.04);
     float a=smoothstep(.48-clCov*.3,.9-clCov*.25,f+float(i)*.012)*clA*exp(-tc*.01)*smoothstep(0.,.8,tc)*(.62+clCov*.5);
     vec3 cc=mix(mix(skM,fogC,.5)*.7,skH*.7+sunC*.35+.08,smoothstep(.5-clCov*.25,1.-clCov*.3,f)*(1.-float(i)*.07))*(.75+.4*pow(sd,3.)+clCov*.25);
     cc=mix(cc,fogc,1.-exp(-.0006*tc*tc));
     c=mix(c,cc,a*.6);}}}
  if(mistA>0.){for(int i=0;i<5;i++){float dz=.25+float(i)*.55;float tm=dz/max(dot(rd,cw),.2);
    if(tm<tH){vec3 q=ro+rd*tm;float f=fbm(q.xz*1.4+q.y*.9+vec2(T*.3,float(i)*5.-T*.12));
     c=mix(c,fogc,smoothstep(.3,.75,f)*mistA*.42*smoothstep(0.,.5,tH-tm));}}}
  if(rainA>0.){c+=(fogC*2.+vec3(.25,.3,.38)+ltn.x*.6)*rainf(p,T)*.45*rainA;}
  if(snowA>0.){c=mix(c,vec3(.95,.97,1.)*(skH*.5+.55),clamp(snowf(p,T)*snowA,0.,1.)*.85);}
 }else{
  float fg=1.-exp(-fogD*min(tH,30.));c=mix(c,fogC,fg);
 }
 if(stage==0&&orb>0.&&(sets&1)!=0){vec3 oc=vec3(0.,stY+1.66,-.24)-ro;float ta=dot(oc,rd);
  if(ta>0.&&ta<tH+.3){float dd=length(oc-rd*ta);c+=vec3(1.,.68,.3)*orb*(exp(-dd*7.)*.3+exp(-dd*1.6)*.07)*exp(-ta*.04);}}
 if(lone.w>0.){float ls=max(dot(rd,lone.xyz),0.);vec2 dd=vec2(dot(rd-lone.xyz,cu),dot(rd-lone.xyz,cv));
  c+=vec3(1.,.95,.85)*lone.w*(pow(ls,4000.)*5.+pow(ls,300.)*.25+.6*exp(-abs(dd.x)*400.)*exp(-abs(dd.y)*30.)+.6*exp(-abs(dd.y)*400.)*exp(-abs(dd.x)*30.));}
 if(part.z>0.){vec3 pc=parts(p);if(int(part.w+.5)==2&&partC.a>.5){float a=clamp(max(pc.r,max(pc.g,pc.b))*4.,0.,1.);c=mix(c,partC.rgb*(.6+.8*a),a);}else c+=pc;}
 O=vec4(max(c,0.),min(tH,1e3));}
