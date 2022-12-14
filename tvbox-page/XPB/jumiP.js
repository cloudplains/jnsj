{
  "author": "Tangsan99999",
  "ua": "Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/604.1",
  "homeUrl": "https://jumi.tv",
  "dcVipFlag": "true",
  "pCfgJs": "https://jumi.tv/static/js/playerconfig.js",
  "pCfgJsR": "[\\W|\\S|.]*?MacPlayerConfig.player_list[\\W|\\S|.]*?=([\\W|\\S|.]*?),MacPlayerConfig.downer_list",
  "dcShow2Vip": {},
  "dcPlayUrl": "true",
  //"cateNode": "//ul[contains(@class,'myui-header__menu')]/li/a[contains(@href, 'type') and not(contains(@href, 'label'))]",
  "cateNode": "//ul[contains(@class,'item nav-list')]/li/a[contains(@href, 'type') and not(contains(@href, 'label'))]",
  "cateName": "/text()",
  "cateId": "/@href",
  "cateIdR": "/type/(\\w+).html",
  "cateManual": {},
  "homeVodNode": "//div[contains(@class, 'col-lg-wide-75')]//ul[contains(@class,'myui-vodlist')]/li//a[contains(@class,'myui-vodlist__thumb')]",
  "homeVodName": "/@title",
  "homeVodId": "/@href",
  "homeVodIdR": "/vod/(\\w+).html",
  "homeVodImg": "/@data-original",
  "homeVodImgR": "\\S+(http\\S+)",
  "homeVodMark": "/span[contains(@class,'pic-text')]/text()",
  "cateUrl": "https://jumi.tv/show/{cateId}/area/{area}/by/{by}/page/{catePg}/year/{year}.html",
  "cateVodNode": "//ul[contains(@class,'myui-vodlist')]//li//a[contains(@class,'myui-vodlist__thumb')]",
  "cateVodName": "/@title",
  "cateVodId": "/@href",
  "cateVodIdR": "/vod/(\\w+).html",
  "cateVodImg": "/@data-original",
  "cateVodImgR": "\\S+(http\\S+)",
  "cateVodMark": "/span[contains(@class,'pic-text')]/text()",
  "dtUrl": "https://jumi.tv/vod/{vid}.html",
  "dtNode": "//div[contains(@class,'col-lg-wide-75')]",
  "dtName": "//div[@class='myui-content__thumb']/a[contains(@class,'myui-vodlist__thumb')]/@title",
  "dtNameR": "",
  "dtImg": "//div[@class='myui-content__thumb']/a[contains(@class,'myui-vodlist__thumb')]/img/@data-original",
  "dtImgR": "\\S+(http\\S+)",
  "dtCate": "//div[@class='myui-content__detail']//span[contains(@class,'text-muted') and contains(text(), '??????')]/following-sibling::*/text()",
  "dtCateR": "",
  "dtYear": "//div[@class='myui-content__detail']//span[contains(@class,'text-muted') and contains(text(), '??????')]/following-sibling::*/text()",
  "dtYearR": "",
  "dtArea": "//div[@class='myui-content__detail']//span[contains(@class,'text-muted') and contains(text(), '??????')]/following-sibling::*/text()",
  "dtAreaR": "",
  "dtMark": "",
  "dtMarkR": "",
  "dtActor": "//div[@class='myui-content__detail']//span[contains(@class,'text-muted') and contains(text(), '??????')]/following-sibling::*/text()",
  "dtActorR": "",
  "dtDirector": "//div[@class='myui-content__detail']//span[contains(@class,'text-muted') and contains(text(), '??????')]/following-sibling::*/text()",
  "dtDirectorR": "",
  "dtDesc": "//span[@class='sketch content']/text()",
  "dtDescR": "",
  "dtFromNode": "//a[@data-toggle='tab' and contains(@href, 'playlist')]",
  "dtFromName": "/text()",
  "dtFromNameR": "",
  "dtUrlNode": "//div[contains(@class,'tab-content')]/div[contains(@id, 'playlist')]",
  "dtUrlSubNode": "//li/a",
  "dtUrlId": "@href",
  "dtUrlIdR": "/play/(\\S+).html",
  "dtUrlName": "/text()",
  "dtUrlNameR": "",
  "playUrl": "https://jumi.tv/play/{playUrl}.html",
  "playUa": "",
  "searchUrl": "https://jumi.tv/index.php/ajax/suggest?mid=1&wd={wd}&limit=10",
  "scVodNode": "json:list",
  "scVodName": "name",
  "scVodId": "id",
  "scVodIdR": "",
  "scVodImg": "pic",
  "scVodMark": "",
  "filter": {
    "1": [
      {
        "key": "cateId",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "?????????","v": "6"},
          {"n": "?????????","v": "7"},
          {"n": "?????????","v": "8"},
          {"n": "?????????","v": "9"},
          {"n": "?????????","v": "10"},
          {"n": "?????????","v": "11"},
          {"n": "?????????","v": "12"},
          {"n": "?????????","v": "20"}
        ]
      },
      {
        "key": "area",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"}
        ]
      },
      {
        "key": "year",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "2022","v": "2022"},
          {"n": "2021","v": "2021"},
          {"n": "2020","v": "2020"},
          {"n": "2019","v": "2019"},
          {"n": "2018","v": "2018"},
          {"n": "2017","v": "2017"},
          {"n": "2016","v": "2016"},
          {"n": "2015","v": "2015"},
          {"n": "2014","v": "2014"},
          {"n": "2013","v": "2013"},
          {"n": "2012","v": "2012"}
        ]
      },
      {
        "key": "by",
        "name": "??????",
        "value": [
          {"n": "??????","v": "time"},
          {"n": "??????","v": "hits"},
          {"n": "??????","v": "score"}
        ]
      }
    ],
    "2": [
      {
        "key": "cateId",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "??????","v": "13"},
          {"n": "??????","v": "23"},
          {"n": "??????","v": "16"},
          {"n": "??????","v": "15"},
          {"n": "??????","v": "22"},
          {"n": "??????","v": "14"},
          {"n": "?????????","v": "24"}
        ]
      },
      {
        "key": "year",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "2022","v": "2022"},
          {"n": "2021","v": "2021"},
          {"n": "2020","v": "2020"},
          {"n": "2019","v": "2019"},
          {"n": "2018","v": "2018"},
          {"n": "2017","v": "2017"},
          {"n": "2016","v": "2016"},
          {"n": "2015","v": "2015"},
          {"n": "2014","v": "2014"},
          {"n": "2013","v": "2013"},
          {"n": "2012","v": "2012"}
        ]
      },
      {
        "key": "by",
        "name": "??????",
        "value": [
          {"n": "??????","v": "time"},
          {"n": "??????","v": "hits"},
          {"n": "??????","v": "score"}
        ]
      }
    ],
    "4": [
      {
        "key": "area",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"}
        ]
      },
      {
        "key": "year",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "2022","v": "2022"},
          {"n": "2021","v": "2021"},
          {"n": "2020","v": "2020"},
          {"n": "2019","v": "2019"},
          {"n": "2018","v": "2018"},
          {"n": "2017","v": "2017"},
          {"n": "2016","v": "2016"},
          {"n": "2015","v": "2015"},
          {"n": "2014","v": "2014"},
          {"n": "2013","v": "2013"},
          {"n": "2012","v": "2012"}
        ]
      },
      {
        "key": "by",
        "name": "??????",
        "value": [
          {"n": "??????","v": "time"},
          {"n": "??????","v": "hits"},
          {"n": "??????","v": "score"}
        ]
      }
    ],
    "3": [
      {
        "key": "area",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"},
          {"n": "??????","v": "??????"}
        ]
      },
      {
        "key": "year",
        "name": "??????",
        "value": [
          {"n": "??????","v": ""},
          {"n": "2022","v": "2022"},
          {"n": "2021","v": "2021"},
          {"n": "2020","v": "2020"},
          {"n": "2019","v": "2019"},
          {"n": "2018","v": "2018"},
          {"n": "2017","v": "2017"},
          {"n": "2016","v": "2016"},
          {"n": "2015","v": "2015"},
          {"n": "2014","v": "2014"},
          {"n": "2013","v": "2013"},
          {"n": "2012","v": "2012"}
        ]
      },
      {
        "key": "by",
        "name": "??????",
        "value": [
          {"n": "??????","v": "time"},
          {"n": "??????","v": "hits"},
          {"n": "??????","v": "score"}
        ]
      }
    ]
  }
}