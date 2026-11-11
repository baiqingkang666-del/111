#version 330
uniform sampler2D C0,C1,C2; uniform vec2 R; uniform float off,warm,T;
out vec4 O;
float h21(vec2 p){p=fract(p*vec2(123.34,456.21));p+=dot(p,p+45.32);return fract(p.x*p.y);}
void main(){
 vec2 uv=gl_FragCoord.xy/R;
 float cw=.6;float x=(uv.x-.5)/cw+off;float idx=floor(x);float fx=fract(x);
 uv.y+=.012*sin(T*23.)*h21(vec2(floor(T*12.),1.));
 float cy=(uv.y-.5)/.56+.5;
 vec3 c=vec3(.012,.01,.009);
 vec2 cu=vec2((fx-.04)/.92,cy);
 if(cu.x>0.&&cu.x<1.&&cu.y>0.&&cu.y<1.){
  int k=int(mod(idx,3.));vec2 tu=vec2(cu.x,cu.y);
  vec3 s=k==0?texture(C0,tu).rgb:k==1?texture(C1,tu).rgb:texture(C2,tu).rgb;
  float l=dot(s,vec3(.3,.59,.11));
  vec3 cold=mix(vec3(l),s,.45)*vec3(.82,.95,1.15);
  vec3 wm=mix(vec3(l),s,1.05)*vec3(1.18,1.,.78)+vec3(.05,.03,.0)*l;
  c=mix(cold,wm,warm);
  vec2 e=abs(cu-.5);c*=smoothstep(.5,.47,max(e.x,e.y));
 }
 // sprocket holes
 float sy=abs(uv.y-.5);
 if(sy>.305&&sy<.36){float hx=fract(x*8.);c=mix(c,vec3(.55,.5,.42)*(.6+.4*warm),step(.25,hx)*step(hx,.75)*step(.315,sy)*step(sy,.35));}
 O=vec4(c*1.4,6.);}
