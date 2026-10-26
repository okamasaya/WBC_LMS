/* =========================================================
 * SECTION 03: Category Selector
 * File: prototype/assets/js/drill/categorySelector.js
 * ========================================================= */

/**
 * ========================================================
 * Category Selector
 *
 * Lv1
 *   ↓
 * Lv2
 *   ↓
 * Lv3
 *
 * ========================================================
 */


/**
 * select の中身を初期化
 */
function resetCategorySelect(selectElement) {

    selectElement.innerHTML = "";

    const option = document.createElement("option");

    option.value = "all";
    option.textContent = "全カテゴリ";

    selectElement.appendChild(option);

}



/**
 * 指定されたカテゴリ順で並べ替える
 *
 * 順序指定にないカテゴリは末尾へ追加する。
 */
function sortCategoriesByOrder(
    categories,
    preferredOrder
) {

    const orderMap = new Map(

        preferredOrder.map(
            (category, index) => [
                category,
                index
            ]
        )

    );


    return [...categories].sort(
        (categoryA, categoryB) => {

            const orderA =
                orderMap.has(categoryA)
                    ? orderMap.get(categoryA)
                    : Number.MAX_SAFE_INTEGER;

            const orderB =
                orderMap.has(categoryB)
                    ? orderMap.get(categoryB)
                    : Number.MAX_SAFE_INTEGER;


            if (orderA !== orderB) {

                return orderA - orderB;

            }


            return categoryA.localeCompare(
                categoryB,
                "ja"
            );

        }
    );

}


/**
 * Category Lv1 の候補を生成
 */
function generateCategoryLv1Options() {

    const lv1Select =
        document.getElementById(
            "category-lv1-select"
        );

    resetCategorySelect(lv1Select);


    const categories = originalQuizData
        .map(q => q.category_lv1)
        .filter(value =>
            value !== null &&
            value !== undefined &&
            String(value).trim() !== ""
        );


    const uniqueCategories =
        [...new Set(categories)]
        .map(value => String(value).trim())
        .sort();


    uniqueCategories.forEach(category => {

        const option =
            document.createElement("option");

        option.value = category;
        option.textContent = category;

        lv1Select.appendChild(option);

    });

}


/**
 * Category Lv2 の候補を生成
 *
 * Lv1で選択された問題だけから
 * Lv2候補を作る。
 */
function updateCategoryLv2Options() {

    const lv1Select =
        document.getElementById(
            "category-lv1-select"
        );

    const lv2Select =
        document.getElementById(
            "category-lv2-select"
        );

    const lv3Select =
        document.getElementById(
            "category-lv3-select"
        );


    resetCategorySelect(lv2Select);
    resetCategorySelect(lv3Select);


    /*
     * Lv1が「全カテゴリ」の場合
     * Lv2、Lv3は選択不可
     */
    if (lv1Select.value === "all") {

        lv2Select.disabled = true;
        lv3Select.disabled = true;

        return;

    }


    /*
     * 選択されたLv1に属する問題だけ抽出
     */
    const filteredQuestions =
        originalQuizData.filter(
            q =>
                String(q.category_lv1 || "") ===
                lv1Select.value
        );


    const categories =
        filteredQuestions
            .map(q => q.category_lv2)
            .filter(value =>
                value !== null &&
                value !== undefined &&
		String(value).trim() !== ""
            );


    //const uniqueCategories =
    //    [...new Set(categories)]
    //    .map(value => String(value).trim())
    //    .sort();

    /*
     * カテゴリ名を文字列へ統一
     */
    const normalizedCategories =
        categories.map(
            value => String(value).trim()
        );


    /*
     * 選択中のLv1に対応した
     * Lv2の表示順を取得
     */
    const preferredOrder =
        CATEGORY_ORDER.lv2[
            lv1Select.value
        ] || [];


    /*
     * 重複を除去し、指定順で並べ替える
     */
    const uniqueCategories =
        sortCategoriesByOrder(

            [...new Set(normalizedCategories)],

            preferredOrder

        );


    uniqueCategories.forEach(category => {

        const option =
            document.createElement("option");

        option.value = category;
        option.textContent = category;

        lv2Select.appendChild(option);

    });


    lv2Select.disabled = false;
    lv3Select.disabled = true;

}


/**
 * Category Lv3 の候補を生成
 *
 * Lv1 + Lv2
 * で絞り込んで候補を作る。
 */
function updateCategoryLv3Options() {

    const lv1Select =
        document.getElementById(
            "category-lv1-select"
        );

    const lv2Select =
        document.getElementById(
            "category-lv2-select"
        );

    const lv3Select =
        document.getElementById(
            "category-lv3-select"
        );


    resetCategorySelect(lv3Select);


    /*
     * Lv2が「全カテゴリ」の場合
     */
    if (lv2Select.value === "all") {

        lv3Select.disabled = true;

        return;

    }


    /*
     * Lv1 + Lv2 で絞込
     */
    const filteredQuestions =
        originalQuizData.filter(q =>

            String(q.category_lv1 || "") ===
                lv1Select.value

            &&

            String(q.category_lv2 || "") ===
                lv2Select.value

        );


    const categories =
        filteredQuestions
            .map(q => q.category_lv3)
            .filter(value =>
                value !== null &&
                value !== undefined &&
                String(value).trim() !== ""
            );


    //const uniqueCategories =
    //    [...new Set(categories)]
    //    .map(value => String(value).trim())
    //    .sort();

    
    /*
     * カテゴリ名を文字列へ統一
     */
    const normalizedCategories =
        categories.map(
            value => String(value).trim()
        );


    /*
     * 選択中のLv1に対応する
     * Lv3設定を取得
     */
    const lv3OrderByLv2 =
        CATEGORY_ORDER.lv3[
            lv1Select.value
        ] || {};


    /*
     * 選択中のLv2に対応した
     * Lv3の表示順を取得
     */
    const preferredOrder =
        lv3OrderByLv2[
            lv2Select.value
        ] || [];


    /*
     * 重複を除去し、指定順で並べ替える
     */
    const uniqueCategories =
        sortCategoriesByOrder(

            [...new Set(normalizedCategories)],

            preferredOrder

        );

    uniqueCategories.forEach(category => {

        const option =
            document.createElement("option");

        option.value = category;
        option.textContent = category;

        lv3Select.appendChild(option);

    });


    /*
     * Lv3データが存在するときだけ有効化
     */
    lv3Select.disabled =
        uniqueCategories.length === 0;

}


/**
 * ========================================================
 * Category Selector 初期化
 * ========================================================
 */
function initializeCategorySelectors() {

    console.log(
        "[CategorySelector] 初期化開始"
    );

    /*
     * Lv1 の選択肢を生成
     */
    generateCategoryLv1Options();


    const lv1Select =
        document.getElementById(
            "category-lv1-select"
        );

    const lv2Select =
        document.getElementById(
            "category-lv2-select"
        );


    /*
     * HTML要素存在確認
     */
    if (!lv1Select) {

        console.error(
            "[CategorySelector] category-lv1-select が見つかりません。"
        );

        return;

    }


    if (!lv2Select) {

        console.error(
            "[CategorySelector] category-lv2-select が見つかりません。"
        );

        return;

    }


    /*
     * Lv1変更
     *
     * Lv1
     * ↓
     * Lv2候補更新
     */
    lv1Select.addEventListener(
        "change",
        function() {

            updateCategoryLv2Options();

        }
    );


    /*
     * Lv2変更
     *
     * Lv2
     * ↓
     * Lv3候補更新
     */
    lv2Select.addEventListener(
        "change",
        function() {

            updateCategoryLv3Options();

        }
    );


    console.log(
        "[CategorySelector] 初期化完了"
    );

}
	



