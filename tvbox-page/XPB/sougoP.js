{
    "author":"20220522",
    "ua": "",
    "homeUrl": "http://sogouyy.cn/",
    "dcPlayUrl": "true",
    "cateManual": {"电影": "dianying","剧集": "dianshiju","综艺": "zongyi","动漫": "dongman","B站": "bilibili"},
    "homeVodNode": "//div[contains(@class, 'module-items')]/div[contains(@class, 'module-item')]",
    "homeVodName": "/div[contains(@class, 'module-item-titlebox')]/a/@title",
    "homeVodId": "/div[contains(@class, 'module-item-titlebox')]/a/@href",
    "homeVodIdR": "/d/(\\w+).html",
    "homeVodImg": "/div[contains(@class, 'module-item-cover')]/div[contains(@class, 'module-item-pic')]/img/@data-src",
    "homeVodImgR": "\\S+(http\\S+)",
    "homeVodMark": "/div[contains(@class,'module-item-text')]/text()",
    
    "cateUrl": "http://sogouyy.cn/s/{cateId}/page/{catePg}.html",
    "cateVodNode": "//div[contains(@class, 'module-items')]/div[contains(@class, 'module-item')]",
    "cateVodName": "/div[contains(@class, 'module-item-titlebox')]/a/@title",
    "cateVodId": "/div[contains(@class, 'module-item-titlebox')]/a/@href",
    "cateVodIdR": "/d/(\\w+).html",
    "cateVodImg": "/div[contains(@class, 'module-item-cover')]/div[contains(@class, 'module-item-pic')]/img/@data-src",
    "cateVodImgR": "\\S+(http\\S+)",
    "cateVodMark": "/div[contains(@class,'module-item-text')]/text()",
  
    "dtUrl": "http://sogouyy.cn/d/{vid}.html",
    "dtNode": "//body",
    "dtName": "//div[contains(@class,'video-info-header')]/h1[@class='page-title']/text()",
    "dtNameR": "",
    "dtImg": "//div[@class=('module-item-pic')]/img/@data-src",
    "dtImgR": "(http\\S+)",
    "dtCate": "//div[contains(@class,'tag-link')]/a/text()",
    "dtCateR": "",
    "dtYear": "//a[@class='tag-link'][1]/text()",
    "dtArea": "//a[@class='tag-link'][2]/text()",
    "dtAreaR": "",
    "dtDesc": "concat(//span[contains(text(), '剧情')]/parent::*/div/span/text())",
    "dtDescR": "",
    "dtActor": "concat(//span[contains(text(), '主演')]/parent::*/div/a/text())",
    "dtActorR": "",
    "dtDirector": "concat(//span[contains(text(), '导演')]/parent::*/div/a/text())",
    "dtDirectorR": "",
    
    "dtFromNode": "//div[contains(@class,'module-tab-items')]/div[2]/div/span",
    "dtFromName": "/text()",
    "dtFromNameR": "",
    "dtUrlNode": "//div[contains(@class,'module-blocklist')]//div[contains(@class,'scroll-content')]",
    "dtUrlSubNode": "/a",
    "dtUrlId": "/@href",
    "dtUrlIdR": "/play/(\\S+).html",
    "dtUrlName": "/span/text()",
    "dtUrlNameR": "",
    "playUrl": "http://sogouyy.cn/play/{playUrl}.html",
    "playUa": "",
    
    "searchUrl": "http://sogouyy.cn/index.php/ajax/suggest?mid=1&wd={wd}&limit=10",
    "scVodNode": "json:list",
    "scVodName": "name",
    "scVodId": "id",
    "scVodIdR": "",
    "scVodImg": "pic",
    "scVodMark": ""
  }