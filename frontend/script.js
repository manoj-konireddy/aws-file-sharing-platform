document.addEventListener(
    "DOMContentLoaded",
    function(){

        if(
            localStorage.getItem("theme")
            === "dark"
        ){
            document.body.classList.add(
                "dark-mode"
            );
        }

    }
);

// Auto-hide messages

setTimeout(() => {

    const messages = document.querySelectorAll(
        ".success-message, .error-message, .delete-message"
    );

    messages.forEach(message => {

        message.style.transition = "0.5s";

        message.style.opacity = "0";

        setTimeout(() => {

            message.remove();

        }, 500);

    });

}, 3000);


// Remove query parameters

if (window.location.search) {

    window.history.replaceState(
        {},
        document.title,
        window.location.pathname
    );

}


// Dark Mode

const darkModeBtn =
    document.getElementById("darkModeBtn");

if(darkModeBtn){

    if(localStorage.getItem("theme") === "dark"){

        document.body.classList.add(
            "dark-mode"
        );

        darkModeBtn.innerHTML =
            "☀️ Light Mode";
    }

    darkModeBtn.addEventListener(
        "click",
        function(e){

            e.preventDefault();

            document.body.classList.toggle(
                "dark-mode"
            );

            if(
                document.body.classList.contains(
                    "dark-mode"
                )
            ){

                localStorage.setItem(
                    "theme",
                    "dark"
                );

                darkModeBtn.innerHTML =
                    "☀️ Light Mode";

            }
            else{

                localStorage.setItem(
                    "theme",
                    "light"
                );

                darkModeBtn.innerHTML =
                    "🌙 Dark Mode";

            }

        }
    );

}


// Drag & Drop Upload

const dropZone =
    document.getElementById(
        "dropZone"
    );

const fileInput =
    document.getElementById(
        "fileInput"
    );

if (
    dropZone &&
    fileInput
) {

    dropZone.addEventListener(
        "dragover",
        function (e) {

            e.preventDefault();

            dropZone.classList.add(
                "drag-over"
            );

        }
    );

    dropZone.addEventListener(
        "dragleave",
        function () {

            dropZone.classList.remove(
                "drag-over"
            );

        }
    );

    dropZone.addEventListener(
        "drop",
        function (e) {

            e.preventDefault();

            fileInput.files =
                e.dataTransfer.files;

            dropZone.classList.remove(
                "drag-over"
            );

        }
    );

}


// Delete Modal

function openDeleteModal(
    fileId,
    fileName,
    fromPage = "home"
){

    document.getElementById(
        "deleteModal"
    ).style.display = "flex";

    document.getElementById(
        "deleteMessage"
    ).innerText =
        `Are you sure you want to delete "${fileName}"?`;

    document.getElementById(
        "confirmDeleteBtn"
    ).href =
        `/delete/${fileId}?from_page=${fromPage}`;

}


function closeModal() {

    document.getElementById(
        "deleteModal"
    ).style.display =
        "none";

}


// Bulk Delete Modal

function openBulkDeleteModal() {

    const selected =
        document.querySelectorAll(
            ".file-checkbox:checked"
        );

    if (
        selected.length === 0
    ) {

        alert(
            "Please select at least one file."
        );

        return;

    }

    let fileNames = "";

    selected.forEach(file => {

        fileNames +=
            file.dataset.filename +
            "<br>";

    });

    document.getElementById(
        "bulkDeleteMessage"
    ).innerHTML =
        `
        Delete ${selected.length} file(s)?

        <br><br>

        ${fileNames}
        `;

    document.getElementById(
        "bulkDeleteModal"
    ).style.display =
        "flex";

}


function closeBulkModal() {

    document.getElementById(
        "bulkDeleteModal"
    ).style.display =
        "none";

}


// Delete Selected Files

function deleteSelectedFiles() {

    const selected =
        document.querySelectorAll(
            ".file-checkbox:checked"
        );

    const ids = [];

    selected.forEach(file => {

        ids.push(
            file.value
        );

    });

    const form =
        document.createElement(
            "form"
        );

    form.method =
        "POST";

    form.action =
        "/bulk-delete";

    const input =
        document.createElement(
            "input"
        );

    input.type =
        "hidden";

    input.name =
        "file_ids";

    input.value =
        ids.join(",");

    form.appendChild(
        input
    );

    document.body.appendChild(
        form
    );

    form.submit();

}


// Selection Mode

const selectModeBtn =
    document.getElementById(
        "selectModeBtn"
    );

const bulkDeleteBtn =
    document.getElementById(
        "bulkDeleteBtn"
    );

const cancelSelectionBtn =
    document.getElementById(
        "cancelSelectionBtn"
    );

const shareSelectedBtn =
    document.getElementById(
        "shareSelectedBtn"
    );

if (
    selectModeBtn
) {

    selectModeBtn.addEventListener(
        "click",
        function () {

            document
                .querySelectorAll(
                    ".file-checkbox"
                )
                .forEach(cb => {

                    cb.classList.remove(
                        "hidden-checkbox"
                    );

                });

            bulkDeleteBtn.style.display =
                "inline-block";

            shareSelectedBtn.style.display =
                "inline-block";

            cancelSelectionBtn.style.display =
                "inline-block";

            selectModeBtn.style.display =
                "none";

        }
    );

}


if (
    cancelSelectionBtn
) {

    cancelSelectionBtn.addEventListener(
        "click",
        function () {

            document
                .querySelectorAll(
                    ".file-checkbox"
                )
                .forEach(cb => {

                    cb.checked =
                        false;

                    cb.classList.add(
                        "hidden-checkbox"
                    );

                });

            bulkDeleteBtn.style.display =
                "none";

            shareSelectedBtn.style.display =
                "none";

            cancelSelectionBtn.style.display =
                "none";

            selectModeBtn.style.display =
                "inline-block";

        }
    );

}


// Close Modal When Clicking Outside

window.onclick =
    function (event) {

        const deleteModal =
            document.getElementById(
                "deleteModal"
            );

        const bulkDeleteModal =
            document.getElementById(
                "bulkDeleteModal"
            );

        if (
            event.target ===
            deleteModal
        ) {

            closeModal();

        }

        if (
            event.target ===
            bulkDeleteModal
        ) {

            closeBulkModal();

        }

    };

function openShareSelectedModal(){

    let selected = [];

    document
        .querySelectorAll(
            ".file-checkbox:checked"
        )
        .forEach(cb => {

            selected.push(
                cb.value
            );

        });

    if(selected.length === 0){

        alert(
            "Select at least one file"
        );

        return;
    }

    document.getElementById(
        "selectedFileIds"
    ).value = selected.join(",");

    document.getElementById(
        "shareModal"
    ).style.display = "flex";
}

async function generateShareLink(
    fileId
){

    const response =
        await fetch(
            `/generate-share-link/${fileId}`
        );

    const data =
        await response.json();

    document.getElementById(
        "shareLinkInput"
    ).value =
        data.share_link;

    document.getElementById(
        "whatsappShare"
    ).href =
        `https://wa.me/?text=${encodeURIComponent(data.share_link)}`;

    document.getElementById(
        "emailShare"
    ).href =
        `mailto:?subject=Shared File&body=${encodeURIComponent(data.share_link)}`;

    document.getElementById(
        "shareLinkModal"
    ).style.display =
        "flex";
}

function copyShareLink(){

    const input =
        document.getElementById(
            "shareLinkInput"
        );

    input.select();

    document.execCommand(
        "copy"
    );

    alert(
        "✅ Share Link Copied"
    );
}

function closeShareModal(){

    document.getElementById(
        "shareLinkModal"
    ).style.display = "none";

}

// Save scroll position
window.addEventListener("beforeunload", function () {
    sessionStorage.setItem("scrollPosition", window.scrollY);
});

// Save scroll position only on list pages
if (
    window.location.pathname === "/" ||
    window.location.pathname === "/my-files"
) {

    window.addEventListener("beforeunload", function () {

        sessionStorage.setItem(
            "scrollPosition",
            window.scrollY
        );

    });

    window.addEventListener("load", function () {

        const scrollPosition =
            sessionStorage.getItem("scrollPosition");

        if (scrollPosition) {

            window.scrollTo(
                0,
                parseInt(scrollPosition)
            );

        }

    });

}