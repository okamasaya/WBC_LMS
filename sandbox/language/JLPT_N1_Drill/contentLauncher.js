function launchContent() {

    const file = selectRandomContent(CONFIG.drillFiles);

    window.location.href = file;

}

function restartDrill() {
    window.location.href = "./index.html";
}
