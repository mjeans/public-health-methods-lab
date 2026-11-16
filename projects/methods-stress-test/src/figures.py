"""Scientific comparisons with Monte Carlo uncertainty, no decorative bars."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from methods import LABELS

COLORS = ["#b57221","#397aab","#007f78","#7a7186"]

def errors(rows, key, mc):
    if key == "bias":
        return [1.96*r[mc] for r in rows]
    return np.array([[max(0,r[key]-r[key+"_lower"]) for r in rows],
                     [max(0,r[key+"_upper"]-r[key]) for r in rows]])

def save(fig, root, name):
    target=root/"assets"
    target.mkdir(exist_ok=True)
    p=target/f"{name}.svg"
    fig.savefig(p,metadata={"Date":None},facecolor="white")
    p.write_text("\n".join(x.rstrip() for x in p.read_text(encoding="utf-8").splitlines())+"\n",encoding="utf-8",newline="\n")
    fig.savefig(target/f"{name}.png",dpi=140,facecolor="white")
    plt.close(fig)

def make_figures(root,rows):
    plt.rcParams.update({"font.family":"DejaVu Sans","font.size":10,"svg.fonttype":"none",
        "svg.hashsalt":"methods-stress-test","axes.spines.top":False,"axes.spines.right":False,
        "text.color":"#183247","axes.labelcolor":"#183247"})
    scenarios=[104,105,106,107]
    labels=["No error","SD 0.75\nIndependent","SD 1.50\nIndependent","SD 1.50\nCorrelated (0.5)"]
    fig,axes=plt.subplots(1,2,figsize=(12,6))
    methods=["one_recall","two_recalls","calibrated","latent_oracle"]
    for j,method in enumerate(methods):
        d=[next(r for r in rows if r["scenario"]==s and r["method"]==method) for s in scenarios]
        x=np.arange(4)+(j-1.5)*.10
        for ax,key,mc in [(axes[0],"bias","bias_mcse"),(axes[1],"coverage","coverage_mcse")]:
            ax.errorbar(x,[r[key] for r in d],yerr=errors(d,key,mc),fmt="o-",lw=1.5,
                        ms=4,capsize=2,color=COLORS[j],label=LABELS[method])
    axes[0].axhline(0,color="#697784",ls="--",lw=1)
    axes[1].axhline(.95,color="#697784",ls="--",lw=1)
    axes[0].set_ylabel("Bias in slope (true slope = 0.5)")
    axes[1].set_ylabel("Coverage of nominal 95% interval")
    axes[1].set_ylim(-.02,1.02)
    for ax in axes:
        ax.set_xticks(range(4),labels);ax.grid(axis="y",alpha=.15)
    fig.suptitle("Two recalls help. They do not remove every error.",x=.04,ha="left",y=.98,fontsize=18,fontweight="bold")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",bbox_to_anchor=(.5,.09),ncol=2,frameon=False)
    fig.text(.04,.025,"2,000 datasets per scenario. 95% Monte Carlo intervals: normal for bias; Wilson for coverage.\nCalibration knows error variance but assumes independent errors. The latent-exposure oracle is not feasible in practice.",fontsize=9,color="#697784")
    fig.subplots_adjust(left=.08,right=.97,bottom=.32,top=.84,wspace=.28)
    save(fig,root,"measurement-error")

    fig,axes=plt.subplots(1,2,figsize=(12,6))
    for j,method in enumerate(["complete_case","ipw","standardized","full_oracle"]):
        d=[next(r for r in rows if r["scenario"]==s and r["method"]==method) for s in [200,201,202]]
        x=np.arange(3)+(j-1.5)*.10
        for ax,key,mc in [(axes[0],"bias","bias_mcse"),(axes[1],"coverage","coverage_mcse")]:
            ax.errorbar(x,[r[key] for r in d],yerr=errors(d,key,mc),fmt="o-",lw=1.5,
                        ms=4,capsize=2,color=COLORS[j],label=LABELS[method])
    axes[0].axhline(0,color="#697784",ls="--",lw=1);axes[0].set_ylabel("Bias in population mean (truth = 0)")
    axes[1].axhline(.95,color="#697784",ls="--",lw=1);axes[1].set_ylabel("Coverage of nominal 95% interval");axes[1].set_ylim(-.02,1.02)
    for ax in axes:
        ax.set_xticks(range(3),["Completely random","Observed X only\n(MAR)","Unobserved error\n(MNAR)"]);ax.grid(axis="y",alpha=.15)
    fig.suptitle("A missingness model is an assumption, not a repair button.",x=.04,ha="left",y=.98,fontsize=17,fontweight="bold")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",bbox_to_anchor=(.5,.09),ncol=2,frameon=False)
    fig.text(.04,.025,"2,000 datasets per scenario. 95% Monte Carlo intervals: normal for bias; Wilson for coverage.\nIPW has known response probabilities only under MCAR/MAR. Full outcomes are an unavailable-in-practice oracle.",fontsize=9,color="#697784")
    fig.subplots_adjust(left=.08,right=.97,bottom=.32,top=.84,wspace=.28)
    save(fig,root,"missingness")

    fig,axes=plt.subplots(1,2,figsize=(12,5.2),sharey=True)
    for ax,schools in zip(axes,[16,48]):
        for j,method in enumerate(["individual_t","school_t"]):
            d=sorted([r for r in rows if r["family"]=="clustering" and r["truth"]==0 and r["schools"]==schools and r["method"]==method],key=lambda r:r["icc"])
            ax.errorbar([r["icc"] for r in d],[r["reject_zero"] for r in d],yerr=errors(d,"reject_zero","reject_zero_mcse"),
                        fmt="o-",capsize=3,color=COLORS[0 if j==0 else 2],label=LABELS[method])
        ax.axhline(.05,color="#697784",ls="--",lw=1);ax.set_xlabel("Intraclass correlation");ax.set_title(f"{schools} schools / 30 pupils each");ax.grid(alpha=.15)
    axes[0].set_ylabel("False-positive rate (true treatment effect = 0)")
    fig.suptitle("More pupils do not create more randomized schools.",x=.04,ha="left",y=.98,fontsize=18,fontweight="bold")
    fig.legend(*axes[0].get_legend_handles_labels(),loc="lower center",bbox_to_anchor=(.5,.09),ncol=2,frameon=False)
    fig.text(.04,.025,"2,000 simulated trials per scenario. Error bars: 95% Wilson Monte Carlo intervals.\nBalanced school assignment, equal cluster sizes, Gaussian outcomes. Dashed line: nominal 5% false-positive rate.",fontsize=9,color="#697784")
    fig.subplots_adjust(left=.09,right=.97,bottom=.29,top=.78,wspace=.2)
    save(fig,root,"clustering")
