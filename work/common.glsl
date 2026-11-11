#define PI 3.14159265
float h11(float n){return fract(sin(n*127.1)*43758.5453);}
float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
vec2 h22(vec2 p){float n=h21(p);return vec2(n,h21(p+n+7.7));}
float vn(vec2 p){vec2 i=floor(p),f=fract(p);f=f*f*(3.-2.*f);
 return mix(mix(h21(i),h21(i+vec2(1,0)),f.x),mix(h21(i+vec2(0,1)),h21(i+1.),f.x),f.y);}
const mat2 M2=mat2(.8,-.6,.6,.8);
float fbm(vec2 p){float a=.5,s=0.;for(int i=0;i<5;i++){s+=a*vn(p);p=M2*p*2.02;a*=.5;}return s;}
float rfbm(vec2 p,int n){float a=.5,s=0.;for(int i=0;i<n;i++){float v=1.-abs(2.*vn(p)-1.);s+=a*v*v;p=M2*p*2.03;a*=.5;}return s;}
mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
// ---- world ----
const vec2 PK4=vec2(7.,17.);          // the "small peak"
float pathX(float z){float s=(z-9.)/12.;float a=mix(1.25,.7,smoothstep(1.,2.,s));
 return a*sin(s*31.4159)*smoothstep(0.,.12,s);}
float terH(vec2 p,int n){
 float z=p.y;
 float land=smoothstep(-2.7,-1.0,z+.35*sin(p.x*.35)+.2*sin(p.x*.9+1.));
 float h=mix(-.5,.1,land)+.04*vn(p*.6)*land;
 vec2 d=(p-vec2(0.,40.))*vec2(.85,1.);float r=length(d);
 float big=pow(max(1.-r/36.,0.),1.5);
 float inl=smoothstep(7.,18.,z);
 float big2=pow(max(1.-length(p-vec2(50.,36.))/26.,0.),1.5);
 if(inl+big>0.){
  float rl=rfbm(p*.06+5.,3);
  float rf=rfbm(p*.2,n);
  h+=(15.*big+11.*big2)*(.5+.55*rl)+(1.1+2.2*big)*inl*rf+inl*(1.-big)*1.2*rl;
  vec2 e=p-PK4;h+=.75*exp(-dot(e,e)/.16);
 }
 return h;}
